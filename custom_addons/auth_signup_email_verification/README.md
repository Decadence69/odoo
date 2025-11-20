# Email Verification for Signup

A professional Odoo 18 module that enhances the standard signup process with mandatory email verification using **Odoo's official signup infrastructure**.

## 🚀 Features

### ✅ Professional Email Verification
- **Mandatory email verification** before account activation
- **Uses Odoo's official signup_token system** - secure & reliable
- **Multi-company compatible** with proper company context
- **Professional email templates** with company branding
- **Automatic token expiration** (configurable via Odoo settings)
- **Website header Sign up button** - automatically appears when signup is enabled

### 🏢 Smart Account Type Selection
- **Company/Individual toggle switch** - choose account type during signup
- **Dynamic form adaptation** - fields change based on selected type
- **Smart partner creation** - creates company + contact structure for business accounts
- **Professional UI** - Bootstrap radio buttons with icons
- **JavaScript-powered UX** - real-time form updates without page reload

### 🎨 Modern UI
- **Bootstrap-styled verification pages** (pending, success, error)
- **Responsive design** that works on all devices
- **Consistent with Odoo's design language**
- **User-friendly status messages** and guidance

### 🔒 Security & Reliability
- **Built on Odoo's official auth_signup module**
- **Uses res.partner model** with standard signup fields
- **Secure token generation** via Odoo's tools.hash_sign()
- **Automatic token cleanup** handled by Odoo
- **No custom models** - follows Odoo standards

## 📋 Requirements

- Odoo 18.0+
- Depends on: `auth_signup`, `portal`

## 🔧 Installation

1. Copy this module to your custom addons directory:
   ```bash
   cp -r auth_signup_email_verification /path/to/odoo/custom-addons/
   ```

2. Update the addons path in your Odoo configuration
3. Restart Odoo
4. Install the module from Apps menu

## 🎯 XPath Implementation Best Practices

### ⚠️ Always Check Server Codebase First!
Before implementing any XPath expressions, **ALWAYS examine the actual Odoo server template structure**:

```bash
# Example: Check auth_signup template structure
cat /path/to/odoo/server/odoo/addons/auth_signup/views/auth_signup_login_templates.xml
```

### ✅ Correct XPath Examples Used in This Module
```xml
<!-- ✅ CORRECT: Based on actual server structure -->
<xpath expr="//label[@for='name']" position="replace">
<xpath expr="//div[contains(@class, 'field-name')]" position="after">
<xpath expr="//form[contains(@class, 'oe_signup_form')]" position="after">

<!-- ❌ WRONG: Assumptions without checking server -->
<xpath expr="//div[hasclass('field-name')]//label[@for='name']" position="replace">
```

### 📋 XPath Development Workflow
1. **Inspect server files** - Check actual template structure in `/server/odoo/addons/`
2. **Use precise selectors** - Prefer specific attributes over complex paths
3. **Test inheritance** - Verify XPath expressions work correctly
4. **Document changes** - Note which server templates are extended

## 💡 Usage

### Enhanced Signup Flow
1. User goes to `/web/signup` (or clicks "Sign up" button in website header)
2. **Selects account type** - Individual or Company using toggle switch
3. **Form adapts dynamically** - shows relevant fields based on selection:
   - **Individual**: Name, Email, Password
   - **Company**: Company Name, Contact Person Name, Email, Password
4. Fills signup form and submits
5. System creates partner structure based on account type:
   - **Individual**: Single partner record
   - **Company**: Company partner + contact person under it
6. Verification email sent using Odoo's mail template system
7. User clicks verification link
8. Account is created automatically using Odoo's signup() method
9. User is auto-logged in and redirected directly to portal (`/my`)

### Website Integration
- **Sign up button** automatically appears in website header when "Free sign up" is enabled
- Button positioned before "Sign in" button with primary Bootstrap styling
- Uses Odoo's official template inheritance (`portal.user_sign_in`)
- Automatic show/hide based on `_get_signup_invitation_scope() == 'b2c'` setting

### Technical Flow
```
User selects account type (Individual/Company)
       ↓
Form adapts dynamically via JavaScript
       ↓
User submits signup form with account type data
       ↓
Partner structure created based on type:
 - Individual: Single partner
 - Company: Company partner + Contact person
       ↓
Signup token generated (using Odoo's _generate_signup_token)
       ↓
Verification email sent
       ↓
User clicks verification link
       ↓
Token verified (using Odoo's _signup_retrieve_partner)
       ↓
User created (using Odoo's signup() method)
       ↓
Auto-login and redirect to portal
```

## 🛠️ Configuration

### Enable Signup
Enable signup in **Settings > Website > Privacy > Customer Account**:
- Select **"Free sign up"** (instead of "On invitation") to allow public registration with email verification
- When enabled, "Sign up" button automatically appears in website header

### Email Template
The module includes a customizable email template:
- `auth_signup_email_verification.mail_template_email_verification`
- Based on `res.partner` model
- Uses Odoo's standard template variables

### URL Routes
- `/web/signup` - Enhanced signup with verification (overrides standard)
- `/auth/verify/email?token=...` - Email verification endpoint
- `/auth/resend/verification?email=...` - Resend verification email

### Security
- Uses Odoo's standard access control
- No additional permissions required
- Partners can be created by public users for signup

## 🔄 Technical Details

### Models Extended
- **res.partner**: Added `email_verified` and `signup_user_data` fields
- **res.users**: Enhanced `signup()` and `_signup_create_user()` methods

### Key Methods
- `res.partner.signup_prepare_with_verification()` - Initiates verification
- `res.partner.get_verification_url()` - Generates verification URL
- `res.partner.complete_email_verification()` - Marks email as verified
- `res.users.signup()` - Enhanced to handle verification flow

### Integration Points
- **Full Odoo compatibility**: Uses official signup infrastructure
- **Multi-company aware**: Users created in proper company context
- **Portal integration**: New users automatically get portal access
- **Mail system**: Uses Odoo's standard mail templates and sending

## 🎯 Why This Approach?

### Professional & Maintainable
- **No custom models** - uses Odoo's standard res.partner
- **Leverages official signup system** - reliable and tested
- **Minimal code footprint** - easy to maintain
- **Standard Odoo patterns** - familiar to developers

### Secure & Reliable
- **Official token system** - cryptographically secure
- **Built-in expiration** - configurable via Odoo settings
- **Standard error handling** - follows Odoo conventions
- **Multi-company safe** - works in enterprise environments

### Extensible & Reusable
- **Clean separation of concerns** - easy to extend
- **Standard extension points** - follows Odoo architecture
- **Reusable across projects** - no hardcoded logic
- **Compatible with other modules** - doesn't conflict
- **Seamless website integration** - automatic header button based on settings

## 🧪 Testing

### Test Scenarios
1. **Normal signup** with email verification
2. **Token expiration** handling
3. **Invalid/manipulated tokens**
4. **Email sending failures**
5. **Multi-company scenarios**
6. **Resend functionality**

### Debug Tips
```bash
# Watch signup process
docker exec [container] tail -f /var/log/odoo/odoo.log

# Check partner signup status
# Settings > Users & Companies > Partners
# Look for partners with signup_type='signup'

# Test token generation
partner._generate_signup_token()

# Verify token manually
self.env['res.partner']._signup_retrieve_partner(token)
```

## 📁 File Structure

```
auth_signup_email_verification/
├── __init__.py
├── __manifest__.py
├── README.md
├── index.py                      # 📋 Module documentation and component index
├── controllers/
│   ├── __init__.py
│   └── main.py                   # 🎯 Enhanced signup controller with account type handling
├── models/
│   ├── __init__.py
│   ├── res_partner.py           # 🏢 Partner extensions for verification & company/individual signup
│   └── res_users.py             # 👤 User signup enhancements
├── views/
│   └── signup_templates.xml     # 🎨 Enhanced signup forms with toggle + verification pages
├── data/
│   └── email_templates.xml      # 📧 Professional email template for verification
└── security/
    └── ir.model.access.csv      # 🔒 Minimal security (uses standard models)
```

### 🔍 Key Files Overview
- **index.py**: Complete module documentation and XPath implementation notes
- **main.py**: Company/individual signup logic with email verification
- **res_partner.py**: Smart partner creation (individual vs company + contact structure)
- **signup_templates.xml**: Dynamic forms with JavaScript toggle and Bootstrap styling

## 🚀 Advantages Over Custom Solutions

### vs Custom Models
- ❌ Custom `email.verification` model
- ✅ Uses standard `res.partner` with signup fields
- ✅ Leverages Odoo's built-in token system
- ✅ No additional database tables

### vs Custom Token Systems
- ❌ Custom token generation and validation
- ✅ Uses Odoo's `tools.hash_sign()` and `tools.verify_hash_signed()`
- ✅ Built-in expiration and security features
- ✅ Configurable via standard Odoo settings

### vs Complex Workflows
- ❌ Multiple models and complex state management
- ✅ Simple extension of existing signup flow
- ✅ Minimal code changes to standard behavior
- ✅ Easy to understand and maintain

## 📄 License

LGPL-3 (GNU Lesser General Public License v3.0)

## 👥 Support

For support, issues, or feature requests, please contact **INTERCOM MALI**.  
Website: https://intercom.ml

---

**Made with ❤️ by INTERCOM MALI - Professional Odoo Development** 