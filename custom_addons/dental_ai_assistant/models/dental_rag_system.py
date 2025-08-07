# dental_rag_system.py
"""
Complete RAG System for Dental Bur Recommendations
This script implements a full RAG system for your dental blog content
"""

import json
import os
import pickle
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb
import google.generativeai as genai

class DentalRAGSystem:
    def __init__(self, api_key: str, persist_directory: str = "./dental_knowledge_db"):
        """Initialize the Dental RAG System"""
        self.api_key = api_key
        self.persist_directory = persist_directory
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize Gemini with updated model name
        genai.configure(api_key=api_key)
        
        # Try different available model names
        model_names = [
            'gemini-1.5-flash',
            'gemini-1.5-pro', 
            'gemini-1.0-pro'
        ]
        
        self.gemini_model = None
        for model_name in model_names:
            try:
                self.gemini_model = genai.GenerativeModel(model_name)
                # Test the model
                test_response = self.gemini_model.generate_content("Test")
                print(f"Successfully initialized Gemini model: {model_name}")
                break
            except Exception as e:
                print(f"Failed to initialize {model_name}: {str(e)}")
                continue
        
        if not self.gemini_model:
            raise Exception("Could not initialize any Gemini model. Please check your API key.")
        
        # Initialize ChromaDB with new API
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        self.collection = None
    
    def process_jsonl_blogs(self, jsonl_file_path: str) -> List[Dict]:
        """Process your JSONL blog file into structured chunks"""
        chunks = []
        
        with open(jsonl_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    blog = json.loads(line.strip())
                    
                    # Handle different JSON structures in your data
                    procedures = blog.get('dental_procedures', blog.get('dentalProcedures', []))
                    burs_tools = blog.get('burs_tools', blog.get('bursAndTools', []))
                    bur_usage = blog.get('bur_usage', blog.get('burUsage', {}))
                    advantages = blog.get('advantages_insights', blog.get('advantagesAndInsights', []))
                    patient_groups = blog.get('patient_groups', blog.get('patientGroups', []))
                    
                    # Create chunks for each procedure
                    for procedure in procedures:
                        # Get usage details for this procedure
                        usage_details = ""
                        if isinstance(bur_usage, dict):
                            usage_details = bur_usage.get(procedure, "")
                            if isinstance(usage_details, list):
                                usage_details = " ".join(usage_details)
                        
                        chunk = {
                            'procedure': procedure,
                            'burs_tools': burs_tools if isinstance(burs_tools, list) else [str(burs_tools)],
                            'usage_details': usage_details,
                            'advantages': advantages if isinstance(advantages, list) else [str(advantages)],
                            'patient_groups': patient_groups if isinstance(patient_groups, list) else [str(patient_groups)],
                            'blog_title': blog.get('title', f'Blog {line_num}'),
                            'content_type': 'procedure_guide',
                            'full_blog_data': blog
                        }
                        chunks.append(chunk)
                    
                    # Also create chunks for specific bur tools if detailed usage is provided
                    if isinstance(bur_usage, dict):
                        for bur_name, usage_info in bur_usage.items():
                            if bur_name not in procedures:  # Avoid duplicating procedure chunks
                                chunk = {
                                    'procedure': f"Using {bur_name}",
                                    'burs_tools': [bur_name],
                                    'usage_details': usage_info if isinstance(usage_info, str) else str(usage_info),
                                    'advantages': advantages,
                                    'patient_groups': patient_groups,
                                    'blog_title': blog.get('title', f'Blog {line_num}'),
                                    'content_type': 'bur_specific_guide',
                                    'full_blog_data': blog
                                }
                                chunks.append(chunk)
                                
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
        
        print(f"Processed {len(chunks)} knowledge chunks from {jsonl_file_path}")
        return chunks
    
    def create_embeddings(self, chunks: List[Dict]) -> tuple:
        """Create embeddings for all chunks"""
        texts = []
        
        for chunk in chunks:
            # Create comprehensive text for embedding
            text_parts = [
                f"Procedure: {chunk['procedure']}",
                f"Tools: {', '.join(chunk.get('burs_tools', []))}",
                f"Usage: {chunk.get('usage_details', '')}",
                f"Advantages: {' '.join(chunk.get('advantages', []))}",
                f"Patient Groups: {' '.join(chunk.get('patient_groups', []))}"
            ]
            
            text = " | ".join([part for part in text_parts if part.split(': ', 1)[1]])  # Only include non-empty parts
            texts.append(text)
        
        print("Creating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        return embeddings, texts
    
    def build_knowledge_base(self, jsonl_file_path: str):
        """Build the complete knowledge base from your blog data"""
        # Process the blog data
        chunks = self.process_jsonl_blogs(jsonl_file_path)
        
        # Create embeddings
        embeddings, texts = self.create_embeddings(chunks)
        
        # Create or recreate the collection
        try:
            self.client.delete_collection("dental_procedures")
        except:
            pass
            
        self.collection = self.client.create_collection(
            name="dental_procedures",
            metadata={"description": "Dental procedures and bur recommendations"}
        )
        
        # Add documents to the collection
        print("Building vector database...")
        for i, (chunk, embedding, text) in enumerate(zip(chunks, embeddings, texts)):
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[text],
                metadatas=[{
                    'procedure': chunk['procedure'],
                    'blog_title': chunk['blog_title'],
                    'content_type': chunk['content_type'],
                    'burs_tools': json.dumps(chunk['burs_tools']),
                    'chunk_data': json.dumps(chunk)
                }],
                ids=[f"chunk_{i}"]
            )
        
        print(f"Knowledge base built with {len(chunks)} chunks")
        return True
    
    def load_existing_knowledge_base(self):
        """Load existing knowledge base"""
        try:
            self.collection = self.client.get_collection("dental_procedures")
            print("Loaded existing knowledge base")
            return True
        except Exception as e:
            print(f"Could not load existing knowledge base: {e}")
            return False
    
    def retrieve_relevant_info(self, query: str, top_k: int = 5) -> Dict:
        """Retrieve relevant information for a query"""
        if not self.collection:
            raise Exception("Knowledge base not loaded. Please build or load knowledge base first.")
        
        # Create query embedding
        query_embedding = self.embedding_model.encode([query])
        
        # Search for similar content
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        return results
    
    def generate_recommendation(self, query: str, top_k: int = 5) -> str:
        """Generate AI recommendation using retrieved context"""
        # Retrieve relevant information
        retrieved_docs = self.retrieve_relevant_info(query, top_k)
        
        # Build context from retrieved documents
        context_parts = []
        for i, (doc, metadata) in enumerate(zip(retrieved_docs['documents'][0], retrieved_docs['metadatas'][0])):
            chunk_data = json.loads(metadata['chunk_data'])
            
            context_part = f"""
            Context {i+1}:
            Procedure: {chunk_data['procedure']}
            Recommended Burs/Tools: {', '.join(chunk_data['burs_tools'])}
            Usage Details: {chunk_data['usage_details']}
            Advantages: {' | '.join(chunk_data['advantages'][:3])}  # Limit for brevity
            """
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Create prompt for Gemini
        prompt = f"""
        You are a dental expert AI assistant helping dentists choose the right burs and tools for their procedures.
        
        Based on the following knowledge from dental procedure guides:
        {context}
        
        Dentist's Question/Situation: {query}
        
        Please provide a professional recommendation including:
        
        1. **Specific Bur/Tool Recommendations**: List the exact burs or tools needed
        2. **Step-by-Step Guidance**: Brief procedure steps if applicable
        3. **Key Advantages**: Why these tools are recommended
        4. **Important Considerations**: Any special notes or precautions
        5. **Alternative Options**: If applicable, mention alternative approaches
        
        Format your response as a clear, professional recommendation that a dentist can immediately act upon.
        Be specific about bur names, sizes, and techniques when possible.
        """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating recommendation: {str(e)}"
    
    def get_recommendation(self, query: str) -> Dict[str, Any]:
        """Main method to get recommendations (for Odoo integration)"""
        try:
            recommendation = self.generate_recommendation(query)
            retrieved_info = self.retrieve_relevant_info(query, 3)
            
            return {
                'success': True,
                'recommendation': recommendation,
                'sources': [metadata['blog_title'] for metadata in retrieved_info['metadatas'][0]],
                'confidence_scores': retrieved_info['distances'][0]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'recommendation': None
            }

# Example usage and testing
def test_system():
    """Test the RAG system"""
    # Initialize system (replace with your actual API key)
    API_KEY = "your-gemini-api-key-here"
    rag_system = DentalRAGSystem(API_KEY)
    
    # Build knowledge base from your JSONL file
    jsonl_file = "your_blog_data.jsonl"  # Replace with your file path
    
    # Build or load knowledge base
    if not rag_system.load_existing_knowledge_base():
        print("Building new knowledge base...")
        rag_system.build_knowledge_base(jsonl_file)
    
    # Test queries
    test_queries = [
        "What burs do I need for zirconia crown removal?",
        "Best tools for composite polishing?",
        "Recommended burs for implant site preparation?",
        "How to prepare a tooth for crown placement?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print('='*50)
        
        result = rag_system.get_recommendation(query)
        
        if result['success']:
            print(result['recommendation'])
            print(f"\nSources: {', '.join(result['sources'])}")
        else:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    test_system()