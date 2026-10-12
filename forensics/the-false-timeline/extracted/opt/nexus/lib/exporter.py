#!/usr/bin/env python3
import hashlib
import os

def derive_emergency_key(machine_id: str, session_uuid: str, event_epoch: int) -> bytes:
    """
    Derives the AES-256 key for emergency export encryption.
    The key relies on tying the execution exactly to the system and session context.
    """
    material = f"{machine_id.strip()}|{session_uuid.strip()}|{int(event_epoch)}"
    return hashlib.sha256(material.encode('utf-8')).digest()

def encrypt_emergency_core(machine_id: str, session_uuid: str, event_epoch: int, plaintext: bytes) -> bytes:
    """
    Export process uses AES-GCM authenticated encryption.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    key = derive_emergency_key(machine_id, session_uuid, event_epoch)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return b'NXKEY_V1' + nonce + ciphertext

