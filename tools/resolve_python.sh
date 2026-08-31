# Sourced, not executed. Sets PY to a command that runs Python 3.11 or newer.
#
# Resolved by RUNNING each candidate rather than locating it. Windows ships App
# Execution Aliases named python and python3 which sit on PATH, are found by
# `command -v` and by shutil.which, and are not interpreters: they print an
# advertisement for the Microsoft Store and exit. An independent validator's
# whole run produced nothing because all thirty-odd steps invoked python3 and
# got that. Only executing a candidate distinguishes the two.
#
# Its own file so CI can test it without running the pipeline.
resolve_python () {
  PY=""
  for cand in python3 python "py -3"; do
    if $cand -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" \
         >/dev/null 2>&1; then PY="$cand"; return 0; fi
  done
  return 1
}
python_not_found_message () {
  echo "no working Python 3.11 or newer was found."
  echo "Tried: python3, python, 'py -3'."
  echo
  echo "On Windows, 'python3' is often a Microsoft Store stub that is on PATH"
  echo "and is not an interpreter. Install Python from python.org, or turn the"
  echo "alias off under Settings > Apps > Advanced app settings > App execution"
  echo "aliases."
}
