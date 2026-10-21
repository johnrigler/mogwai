# Stable controls and a movable working root — October 20, 2026

Proposed local layout from the conversation; not an implemented launcher or
health dashboard, and not a change to the existing listener commands.

| Surface | Proposed port | Job |
| --- | --- | --- |
| Mogwai control/status window | `127.0.0.1:1132` | Stable home for tools, repo selection and a visual "is everything running?" checklist |
| Working document window | `127.0.0.1:39632` | Serve the selected repo/directory through the shared PHP/SB Shell router |

The work port stays fixed. Its document root moves. Switching workspaces can
be as direct as stopping the one managed working listener and restarting it
with `php -S 127.0.0.1:39632 -t SELECTED_ROOT ROUTER`, then navigating/reloading
the working window. The router stays in Mogwai; archive/source files stay in
their own repositories. No copies, per-repo app stack or new port allocation
are needed just to change the working directory.

The operator reports that starting SB Shell at the whole home directory
failed under the amount of work there. The exact failure/cost was not measured
in this conversation. Keep the working root focused on the selected repo or
subdirectory; do not recursively catalog/browse the whole home just to choose
a workspace. Keep the stable controls small. Additional per-repo listeners
are not required for this layout; separate ports remain appropriate only for
services that actually need to run independently.

Bash remains the operator's cross-repository workspace. Use ordinary paths,
`cd`, source/include and existing `a.*`, `d.*` or `m.*` functions to reach
tools and records in other checkouts. The HTTP document root controls what
that browser listener serves; it does not redefine shell filesystem access.
A small inspectable Bash function can manage listener switching. Preserve
native function naming/snapshots rather than add a service framework just to
coordinate two local browser windows.

The control listener/process must survive independently of that restart.
Do not have the working listener terminate itself and depend on completing
the restart afterward. A small launcher/controller outside it should manage
only the listener it started, retain the chosen root and report start/stop
success or failure. Keep the repo/root selection operator-controlled and
handle directory names as arguments, not interpolated shell code.

The status view should show observed results separately: controller reachable,
working listener reachable, selected root, PHP/module readiness and optional
tool readiness such as FileProxy and the signature verifier. A running HTTP
listener does not establish that every dependency or signing check works.
Start from the existing SB Shell setup checker and workbench; do not create
a new dependency/manifest framework for this proposal.

`1132` and `39632` are separate browser origins. A dashboard's browser-side
fetches need an intentional interface; server-side local checks can avoid
adding broad CORS access. Preserve existing loopback/Host checks and keep
private profile databases outside every served root. No authentication changes,
automatic shell execution API or listener supervisor were built tonight.

When selecting Daisy 2026 for this task, navigate the working window to
`/43/`; SB Shell assembles `43/1_01.html` first. Switching a server root can
make the previous URL path invalid, so open the selected root's appropriate
entry path after restart rather than assuming the old path still exists.

Existing documentation uses port `39692` for the current archive listener.
Do not silently change that live setup. The proposed `39632` is the working
window in the next launcher design; these are intentionally different values.

See [signed-edition work](SIGNED-EDITIONS.md) and
[Daisy's current handoff](https://github.com/johnrigler/daisy_2026/blob/main/43/1_01.html).
