#!/usr/bin/env python
"""Generate and verify a valid Fernet encryption key."""
import os
from pathlib import Path
from cryptography.fernet import Fernet


def generate_key() -> str:
    """Generate a new Fernet key."""
    key_bytes = Fernet.generate_key()
    return key_bytes.decode("utf-8")


def verify_key(key_str: str) -> bool:
    """Verify the key is valid."""
    try:
        key_with_padding = key_str.strip() + ("=" * (-len(key_str.strip()) % 4))
        cipher = Fernet(key_with_padding.encode("utf-8"))
        # Test encrypt/decrypt
        test_data = b"test"
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        return decrypted == test_data
    except Exception as e:
        print(f"❌ Key validation failed: {e}")
        return False


def main():
    env_file = Path(__file__).parent / ".env"

    # Generate new key
    new_key = generate_key()
    print(f"✅ Generated new Fernet key")
    print(f"   Key: {new_key}")

    # Verify it works
    if verify_key(new_key):
        print(f"✅ Key verification passed")
    else:
        print(f"❌ Key verification failed")
        return

    # Update .env file
    if env_file.exists():
        content = env_file.read_text()
        if "ACCESS_TOKEN_ENCRYPTION_KEY" in content:
            # Replace existing
            lines = content.split("\n")
            updated_lines = []
            for line in lines:
                if line.startswith("ACCESS_TOKEN_ENCRYPTION_KEY"):
                    updated_lines.append(f"ACCESS_TOKEN_ENCRYPTION_KEY={new_key}")
                else:
                    updated_lines.append(line)
            env_file.write_text("\n".join(updated_lines))
            print(f"✅ Updated .env file")
        else:
            # Append
            with open(env_file, "a") as f:
                f.write(f"\nACCESS_TOKEN_ENCRYPTION_KEY={new_key}\n")
            print(f"✅ Added to .env file")
    else:
        # Create .env
        env_file.write_text(f"ACCESS_TOKEN_ENCRYPTION_KEY={new_key}\n")
        print(f"✅ Created .env file")

    print(f"\n📝 File location: {env_file}")
    print(f"🚀 Restart your server for changes to take effect")


if __name__ == "__main__":
    main()
