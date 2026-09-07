EM-Audio - independent reproduction package
===========================================

Thank you for running this. What helps is not that it passes: it is knowing what
happens on your machine. Earlier reproductions each found real defects, and they
are published in the paper as results rather than quietly fixed.

A run that fails and is reported is worth more than a run that was made to pass.


BEFORE YOU START, ON ANY SYSTEM
-------------------------------

Unpack to a SHORT path:  C:\em-audio  or  ~/em-audio

Windows still defaults to MAX_PATH 260, and one of our tools truncates output
paths past about 200 characters without reporting an error. Unpacking inside
Downloads, in a folder repeating the archive name, has already cost a run.


WINDOWS: double click
---------------------

    Reproducir_en_Windows.cmd

It lists what is missing and ASKS before installing anything. It installs what
is needed with winget, including Git, since run_all.sh needs bash and Windows
does not ship one; downloads c2patool; builds a virtual environment; runs
everything; and leaves one zip named after the machine.

To check without running the experiments, from PowerShell:

    .\Reproducir_en_Windows.cmd -Check


macOS: double click
-------------------

    Reproducir_en_Mac.command

If Finder refuses to open it, right-click and choose Open. It offers to install
what is missing with Homebrew, after asking, and does the rest as above.


LINUX, or the terminal on any system
------------------------------------

    cd em-audio
    python3 tools/repro_selftest.py        # runs no experiments; names what is missing
    pip install -r requirements.txt
    ./run_all.sh 2>&1 | tee run_all_output.txt
    python3 tools/verify_reproduction.py 2>&1 | tee verify_output.txt

You need on PATH: ffmpeg, ffprobe, node, espeak-ng and c2patool.

On Windows, if "python3" does nothing useful, use "python" or "py -3": that name
is usually a Microsoft Store alias which sits on PATH and is not an interpreter.


HOW LONG
--------

About 25 minutes, plus a 322 MB corpus download the first time.


WHAT TO EXPECT AT THE END
-------------------------

verify_reproduction.py may exit zero or non-zero, and both are results.

Our reference was produced on a Mac with Apple Silicon and FFmpeg 9.0.1 from
Homebrew. On a similar machine you may reproduce everything exactly. On a
different FFmpeg build we expect the measured MP3 kernel reach to differ, which
is precisely what the paper claims: that number is a property of the build and
not a constant of the codec.

If a step fails, the log names the step and its exit code, and repeats the list
at the end. You can also run:

    python3 tools/explain_failure.py run_all_output.txt


WHAT TO SEND BACK
-----------------

The Windows and macOS scripts leave the archive ready. If you ran by hand:

  run_all_output.txt
  verify_output.txt
  results/PREFLIGHT.txt
  everything in results/machine_readable/

Send it whatever the exit code was, including a run that produced nothing. A log
with no results is exactly what located one of the defects.
