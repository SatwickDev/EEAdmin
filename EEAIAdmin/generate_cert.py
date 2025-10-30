"""
Generate self-signed SSL certificate for local HTTPS development
This allows camera access and other secure features to work on localhost
"""

from OpenSSL import crypto
import os

def generate_self_signed_cert(cert_dir="ssl"):
    """
    Generate a self-signed SSL certificate for localhost
    """
    # Create ssl directory if it doesn't exist
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
        print(f"✅ Created directory: {cert_dir}")
    
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    
    # Check if certificate already exists
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"✅ Certificate already exists:")
        print(f"   - Certificate: {cert_file}")
        print(f"   - Private Key: {key_file}")
        return cert_file, key_file
    
    # Create a key pair
    print("🔐 Generating RSA key pair (2048 bits)...")
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    
    # Create a self-signed certificate
    print("📜 Creating self-signed certificate...")
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "FinStack Development"
    cert.get_subject().OU = "Development"
    cert.get_subject().CN = "localhost"
    
    # Add Subject Alternative Names for local development
    cert.add_extensions([
        crypto.X509Extension(b"subjectAltName", False, 
                           b"DNS:localhost,DNS:127.0.0.1,DNS:192.168.0.12,IP:127.0.0.1,IP:192.168.0.12")
    ])
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for 1 year
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')
    
    # Write certificate to file
    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    print(f"✅ Certificate saved: {cert_file}")
    
    # Write private key to file
    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    print(f"✅ Private key saved: {key_file}")
    
    print("\n" + "="*60)
    print("🎉 Self-signed certificate generated successfully!")
    print("="*60)
    print("\n📝 IMPORTANT: Trust the certificate in your browser:")
    print("   1. Open Chrome/Edge and navigate to: chrome://settings/security")
    print("   2. Scroll down to 'Manage certificates'")
    print("   3. Go to 'Trusted Root Certification Authorities' tab")
    print("   4. Click 'Import' and select the cert.pem file")
    print("   5. Restart your browser")
    print("\n   OR simply click 'Advanced' -> 'Proceed to localhost' when")
    print("   you see the security warning in your browser.")
    print("\n🚀 Your app will now run on: https://localhost:5000")
    print("   and https://192.168.0.12:5000")
    print("="*60 + "\n")
    
    return cert_file, key_file

if __name__ == "__main__":
    try:
        generate_self_signed_cert()
    except ImportError:
        print("❌ Error: pyOpenSSL library not found")
        print("📦 Installing pyOpenSSL...")
        import subprocess
        subprocess.check_call(["pip", "install", "pyOpenSSL"])
        print("✅ pyOpenSSL installed. Running certificate generation...")
        generate_self_signed_cert()
