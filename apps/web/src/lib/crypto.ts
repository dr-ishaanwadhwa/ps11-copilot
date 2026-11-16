/**
 * WebCrypto Subtle Helper for Sovereign Vault Envelope (ADR-001)
 * Enforces PBKDF2-HMAC-SHA256 (100k iterations) & AES-256-GCM authenticated encryption.
 */

const MAGIC = new TextEncoder().encode('SOV_VAULT_V1\0'); // 12 bytes
const SALT_LENGTH = 16;
const NONCE_LENGTH = 12;
const ITERATIONS = 100_000;

export async function deriveKeyFromPin(pin: string, salt: Uint8Array): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const pinBuffer = enc.encode(pin);

  const baseKey = await crypto.subtle.importKey(
    'raw',
    pinBuffer,
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt as BufferSource,
      iterations: ITERATIONS,
      hash: 'SHA-256',
    },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

export async function encryptPayload(data: unknown, pin: string): Promise<ArrayBuffer> {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
  const nonce = crypto.getRandomValues(new Uint8Array(NONCE_LENGTH));
  const key = await deriveKeyFromPin(pin, salt);

  const jsonStr = JSON.stringify(data);
  const plaintext = new TextEncoder().encode(jsonStr);

  const ciphertext = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: nonce as BufferSource,
    },
    key,
    plaintext
  );

  // Layout: [MAGIC (12B)] + [SALT (16B)] + [NONCE (12B)] + [CIPHERTEXT + 16B TAG]
  const totalLength = MAGIC.length + salt.length + nonce.length + ciphertext.byteLength;
  const result = new Uint8Array(totalLength);

  let offset = 0;
  result.set(MAGIC, offset);
  offset += MAGIC.length;

  result.set(salt, offset);
  offset += salt.length;

  result.set(nonce, offset);
  offset += nonce.length;

  result.set(new Uint8Array(ciphertext), offset);

  return result.buffer;
}

export async function decryptPayload<T = unknown>(envelope: ArrayBuffer, pin: string): Promise<T> {
  const bytes = new Uint8Array(envelope);

  if (bytes.length < MAGIC.length + SALT_LENGTH + NONCE_LENGTH + 16) {
    throw new Error('Invalid envelope length: payload corrupted or truncated.');
  }

  // Validate magic header
  for (let i = 0; i < MAGIC.length; i++) {
    if (bytes[i] !== MAGIC[i]) {
      throw new Error('Invalid envelope header: magic mismatch.');
    }
  }

  let offset = MAGIC.length;
  const salt = bytes.slice(offset, offset + SALT_LENGTH);
  offset += SALT_LENGTH;

  const nonce = bytes.slice(offset, offset + NONCE_LENGTH);
  offset += NONCE_LENGTH;

  const ciphertext = bytes.slice(offset);

  const key = await deriveKeyFromPin(pin, salt);

  try {
    const plaintextBuffer = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: nonce as BufferSource,
      },
      key,
      ciphertext as BufferSource
    );

    const jsonStr = new TextDecoder().decode(plaintextBuffer);
    return JSON.parse(jsonStr) as T;
  } catch {
    throw new Error('Decryption failed: Incorrect PIN or tampered envelope.');
  }
}

export async function generateSha256(data: string): Promise<string> {
  const enc = new TextEncoder();
  const buffer = enc.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
