EM-Audio - independent reproduction package
===========================================

Thank you for running this. What helps us is not that it passes: it is knowing
what happens on your machine. Two earlier reproductions each found real defects,
and both are published in the paper as results rather than quietly fixed.

A run that fails and is reported is worth more than a run that was made to pass.

BEFORE YOU START
----------------

Unpack this to a SHORT path. C:\em-audio is ideal.

Windows still defaults to MAX_PATH 260, and one of our tools truncates output
paths past about 200 characters without reporting an error. Unpacking inside
Downloads, in a folder that repeats the archive name, has already cost one
reproducer a run.

WHAT TO DO
----------

1) Check the tools. This runs no experiments:

       cd em-audio
       python tools\repro_selftest.py

   If "python" does not work, try "py -3". The check tells you which of the
   three interpreter names the pipeline will actually use, and names anything
   that is missing along with how to install it.

2) Install and run:

       pip install -r requirements.txt
       bash run_all.sh 2>&1 | tee run_all_output.txt
       python tools\verify_reproduction.py 2>&1 | tee verify_output.txt

   Git Bash provides bash on Windows. WSL works too.

You need on PATH: ffmpeg, ffprobe, node, espeak-ng and c2patool. Expect about
25 minutes, plus a 322 MB corpus download the first time.

WHAT TO EXPECT AT THE END
-------------------------

verify_reproduction.py may exit non-zero. That is a result, not a failure on
your part, and it is the interesting case.

Our own Windows runs do not reproduce the measured MP3 kernel reach: 1,541
source samples against the 1,555 the reference build measured, on the same
FFmpeg version number. Both sit inside the 2,304 declared, so the declaration
held. That difference is what the paper claims, measured on another machine.

If a step fails, the log now names the step and its exit code, and repeats the
list at the end.

WHAT TO SEND BACK
-----------------

  run_all_output.txt
  verify_output.txt
  results/PREFLIGHT.txt
  everything in results/machine_readable/

Send it whatever the exit code was, including a run that produced nothing. One
earlier bundle contained no results at all, and that log was exactly what
located the defect.
