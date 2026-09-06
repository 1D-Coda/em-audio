# Sourced, not executed. Resolves a usable Python interpreter into $PY.
#
# Resolution is by RUNNING each candidate, not by locating it. An independent
# validator's Windows run produced none of the thirteen result files: every step
# invoked python3, hit the Microsoft Store App Execution Alias, printed the
# Store advertisement and did no work. That alias is on PATH, so `command -v`
# finds it and shutil.which reports it. Only executing it tells you.
#
# Kept in its own file so it can be tested directly. The first attempt inlined
# it in run_all.sh and there was no way to exercise it without a 45-minute run.
resolve_python () {
  PY=""
  for cand in python3 python "py -3"; do
    if $cand -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)" \
         >/dev/null 2>&1; then
      PY="$cand"
      return 0
    fi
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
