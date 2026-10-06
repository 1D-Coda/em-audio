EM-Audio: independent validation on Windows
===========================================

Thank you for doing this. It takes about 25 to 40 minutes of machine time and
almost none of yours.


WHAT YOU NEED
-------------

Docker Desktop, from docker.com. Open it once and wait until it says "Running".

That is all. You do not need Python, Git, FFmpeg or Node. All of that is inside
the container, at pinned versions, and the code that runs comes inside this
same ZIP.


WHAT TO DO
----------

1. Extract this ZIP anywhere you like.
2. Double-click   CHECK_ONLY.cmd
   It checks your machine and runs nothing. It takes seconds.
3. If that goes well, double-click   RUN_EM_AUDIO_VALIDATION.cmd
4. When it finishes, send me   SEND_THIS_BACK.zip


HOW TO READ THE RESULT
----------------------

Two of the codes are success. This matters:

   0   everything passed and the claims held on your machine
   3   everything passed, and one footprint claim does NOT hold on your FFmpeg
   1   something else failed, and that is a defect I want to see
  10   Docker is missing or not running; nothing scientific was attempted

A 3 IS NOT YOUR FAULT. It is the central result of the paper, measured again.

The paper holds that those numbers depend on the FFmpeg build and must be
recalibrated for each one. An independent reproduction on FFmpeg 8.0.1 already
measured the MP3 encoder reaching 4,317 samples against 2,304 claimed, and that
is published as a finding. The claim was not widened to make it pass.

If your machine gives 3, it confirms that thesis. If it gives 0, that is also
information.


WHAT TO SEND ME
---------------

Only   SEND_THIS_BACK.zip

It holds your results, your machine report and the two logs. It is built
automatically.

Send it however it turns out. A run that fails and is reported is worth more
than one that was adjusted to pass. The previous reproduction ended with an
error and found two real defects that are now published.


IF SOMETHING GETS STUCK
-----------------------

"Docker is not running": open Docker Desktop and wait for the whale icon.

If Windows asks you to enable virtualization or the WSL2 backend, the script
tells you before it starts, not thirty minutes in.

If PowerShell complains about scripts, the .cmd files already handle that. You
do not have to type any command.

Anything else: send me the window as it is, without fixing it. A reported error
helps me more than one that was worked around.


AN HONEST WARNING
-----------------

These Windows scripts have never run on a real Windows machine with Docker
Desktop. The logic that runs inside the container is tested, and the package
is checked in continuous integration, but the Windows wrapper is not.

If it breaks, that is the wrapper's fault and not yours. Let me know.
