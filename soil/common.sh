# Common functions for soil/

log() {
  echo "$@" 1>&2
}

log-context() {
  local label=$1

  log ''
  log "$label: running as user '$(whoami)' on host '$(hostname)' in dir $PWD"
  log ''
}

dump-env() {
  env | grep -v '^encrypted_' | sort
}

readonly SOIL_USER='travis_admin'
readonly SOIL_HOST='travis-ci.oilshell.org'
readonly SOIL_USER_HOST="$SOIL_USER@$SOIL_HOST"

html-head() {
  PYTHONPATH=. doctools/html_head.py "$@"
}

# NOTE: soil-html-head and table-sort-html-head are distinct, because they
# collide with <td> styling and so forth

soil-html-head() {
  local title="$1"
  local web_base_url=${2:-'/web'}

  html-head --title "$title" \
    "$web_base_url/base.css?cache=0" "$web_base_url/soil.css?cache=0"
}

table-sort-html-head() {
  local title="$1"
  local web_base_url=${2:-'/web'}

  html-head --title "$title" \
    "$web_base_url/base.css?cache=0" \
    "$web_base_url/ajax.js?cache=0" \
    "$web_base_url/table/table-sort.css?cache=0" "$web_base_url/table/table-sort.js?cache=0" 
}

# Used by mycpp/build.sh and benchmarks/auto.sh
find-dir-html() {
  local dir=$1
  local out_name=${2:-index}

  local txt=$dir/$out_name.txt
  local html=$dir/$out_name.html

  find $dir -type f | sort > $txt
  echo "Wrote $txt"

  # Note: no HTML escaping.  Would be nice for Oil.
  find $dir -type f | sort | gawk -v dir="$dir" '
  match($0, dir "/(.*)", m) {
    url = m[1]
    printf("<a href=\"%s\">%s</a> <br/>\n", url, url)
  }
  ' > $html

  echo "Wrote $html"
}
