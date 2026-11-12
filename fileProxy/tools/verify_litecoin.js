#!/usr/bin/env node
"use strict";
// Verifies Litecoin compact signed messages using Chisel's existing elliptic bundle.
// CHISEL_ELLIPTIC_PATH points at the checked-out Chisel vendor/elliptic-6-6-1.min.js.
const fs = require("node:fs");
const crypto = require("node:crypto");
const path = require("node:path");

function sha256(data) { return crypto.createHash("sha256").update(data).digest(); }
function sha256d(data) { return sha256(sha256(data)); }
function varint(n) {
  if (n < 253) return Buffer.from([n]);
  if (n <= 65535) { const b = Buffer.alloc(3); b[0] = 253; b.writeUInt16LE(n, 1); return b; }
  throw Error("Message too long");
}
function base58check(payload) {
  const bytes = Buffer.concat([payload, sha256d(payload).subarray(0, 4)]);
  const alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  let n = BigInt("0x" + bytes.toString("hex")), out = "";
  while (n > 0n) { out = alphabet[Number(n % 58n)] + out; n /= 58n; }
  for (const b of bytes) { if (b !== 0) break; out = "1" + out; }
  return out;
}
function verify(message, signature, bundle) {
  const elliptic = require(path.resolve(bundle));
  if (!elliptic || !elliptic.ec) throw Error("Chisel elliptic bundle not found");
  const raw = Buffer.from(signature, "base64");
  if (raw.length !== 65 || raw.toString("base64") !== signature || raw[0] < 27 || raw[0] > 34)
    throw Error("Invalid compact signature");
  const header = raw[0] - 27, recid = header & 3, compressed = !!(header & 4);
  const text = Buffer.from(message, "utf8");
  const prefix = Buffer.from("\x19Litecoin Signed Message:\n", "utf8");
  const digest = sha256d(Buffer.concat([prefix, varint(text.length), text]));
  const ec = new elliptic.ec("secp256k1");
  const sig = { r: raw.subarray(1, 33).toString("hex"), s: raw.subarray(33, 65).toString("hex") };
  const key = ec.recoverPubKey(digest, sig, recid);
  if (!ec.verify(digest, sig, key)) throw Error("Invalid signature");
  const pub = Buffer.from(key.encode("array", compressed));
  const h160 = crypto.createHash("ripemd160").update(sha256(pub)).digest();
  return base58check(Buffer.concat([Buffer.from([0x30]), h160]));
}
function main() {
  const bundle = process.env.CHISEL_ELLIPTIC_PATH;
  if (!bundle) throw Error("CHISEL_ELLIPTIC_PATH must point to Chisel vendor/elliptic-6-6-1.min.js");
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  if (typeof input.message !== "string" || typeof input.signature !== "string")
    throw Error("Invalid verifier input");
  process.stdout.write(JSON.stringify({address: verify(input.message, input.signature, bundle)}) + "\n");
}
if (require.main === module) {
  try { main(); }
  catch (error) { process.stderr.write(String(error.message) + "\n"); process.exitCode = 1; }
}
module.exports = {verify};
