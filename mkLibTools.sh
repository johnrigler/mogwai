

# m.get-libTools() {
declare -F | cut -c 12- | grep -v "^_" | grep -v "^-" 
for fn in $(compgen -A function | grep '^d.'); do declare -f "$fn"; done
 #  }
