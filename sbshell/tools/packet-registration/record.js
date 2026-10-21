// Plain browser functions shared by the registration page and focused checks.
export function requireRecord(record) {
  if (!record.filename || !/^[a-f0-9]{64}$/i.test(record.sha256 || '')) throw Error('Select the final PDF first.');
  if (!record.certledger_id || !record.transaction_id) throw Error('Enter the CertLedger ID and the returned transaction ID.');
  const url = new URL(record.transaction_url);
  if (!['https:', 'http:'].includes(url.protocol)) throw Error('Use an HTTP or HTTPS transaction URL.');
  return record;
}

export function emailBody(record) {
  requireRecord(record);
  return [
    'Please find attached ' + record.filename + ', our Experian dispute packet with its full appendix.',
    'The appendix includes the Centro welcome packet and the prior certified-mail return receipt, arranged with the other exhibits in chronological order.',
    '',
    'CertLedger record: ' + record.certledger_id,
    'SHA-256 of the attached PDF: ' + record.sha256,
    'Ledger: ' + record.network,
    'Transaction: ' + record.transaction_id,
    'Transaction reference: ' + record.transaction_url,
    '',
    'The SHA-256 fingerprint of this exact PDF has been registered with the CertLedger record identified above. A shorter paper edition will reference this email for the additional exhibits.',
    'Please review the substance of the dispute and respond in writing.'
  ].join('\n');
}

export function emailDispatch(record, destination, sentAt) {
  requireRecord(record);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(destination)) throw Error('Enter the actual destination email address.');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$/.test(sentAt) || !Number.isFinite(Date.parse(sentAt))) {
    throw Error('Enter the actual sent timestamp with a time zone, using YYYY-MM-DDTHH:MM:SS-06:00 or Z.');
  }
  return {
    to: destination, sent_at: sentAt, pdf: record.filename, sha256: record.sha256,
    certledger_id: record.certledger_id, transaction_id: record.transaction_id,
    transaction_url: record.transaction_url
  };
}

export function phpDispatch(value) {
  const quote = text => "'" + String(text).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
  return '<?php\n// Actual email dispatch; exported after sending.\nreturn [\n' +
    Object.entries(value).map(([key, text]) => '    ' + quote(key) + ' => ' + quote(text)).join(',\n') + '\n];\n';
}

export function requireMailRecord(record, email, destination, sentAt) {
  requireRecord(record);
  emailDispatch(email, destination, sentAt);
  if (record.sha256.toLowerCase() === email.sha256.toLowerCase()) throw Error('Choose the separate, shorter mail PDF.');
  if (record.network.toLowerCase() === email.network.toLowerCase() && record.transaction_id.toLowerCase() === email.transaction_id.toLowerCase()) {
    throw Error('The mail PDF needs its own ledger transaction, separate from the email PDF.');
  }
  return record;
}

export function receiptLines(record) {
  requireRecord(record);
  return [
    'CERTLEDGER TRANSACTION',
    record.edition.toUpperCase() + ' PDF',
    record.filename,
    'Record: ' + record.certledger_id,
    'Sticker: ' + (record.sticker_id || 'not recorded'),
    'SHA-256:', record.sha256.slice(0, 32), record.sha256.slice(32),
    'Ledger: ' + record.network,
    'Transaction: ' + record.transaction_id,
    'Scan transaction QR below.'
  ];
}
