# Static transaction inventories

The public archive is the interface. Producers may stop independently; Apache or
an IPFS gateway can continue serving the last published files. PHP is not needed.

Run `bash ~/mogwai/tools/publish-files.sh` on rigler.org. It uses
`CHISEL_DATA_ROOT` from the same optional bsv.env as the scanner, or defaults
to ~/chisel_data. An explicit first argument overrides the root.

Example cron entry (install manually with crontab -e):

```cron
* * * * * /bin/bash "$HOME/mogwai/tools/publish-files.sh"
```

The script atomically writes transactions/.files (one direct currency
directory name per line) and transactions/<currency>/.files (one recognized
transaction JSON basename per line). No JSON body is read or altered. Symlinked
directories and files are not included. Unchanged inventories are not rewritten.
A failed currency refresh preserves any previous inventory, reports a warning,
and does not block other currencies. The root inventory lists every eligible
currency directory, including failed ones, so readers can try the old inventory
or HTTP listing. The script exits 1 for partial publication, after writing the
root inventory, so cron can report errors. The transaction root is published last. This is not a database snapshot;
concurrent producer changes appear on a subsequent run.

Allow HTTP GET of these specific .files files on Apache with CORS for Chisel.
Do not enable all dotfiles or expose private configuration directories.
If the site denies dotfiles, allow the exact basename .files within this
public tree using its Apache configuration, without relaxing restrictions on
other hidden files. Verify from Chisel's browser.

Archive inventory does not indicate scanner activity, transaction validity,
or curation status. Static publication is independent from both FileProxy and
the scanner. Future curation must be a separate persisted visibility policy.
