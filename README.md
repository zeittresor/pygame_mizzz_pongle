# pygame_mizzz_pongle
Free Pongle/Pegl/Pong/Plop/Flipper style game written in python using pygame..

![mizzz_pongle_v1_1](https://github.com/user-attachments/assets/b5cf0f20-cb9f-4b59-a5aa-76c516c843c0)

This is my first game written in python using the pygame repository..

Goal of the Game is to shot each visible pylone using the single ball you descide
in wich direction it should fall, but be aware the wind direction and its speed is
changing all the time (visible in the top right corner). You can control the paddles
left and right to the exit holes using the mousebuttons (or with arrows or WSAD keys).

It is very simple to "mod" this game using own files.
To do this just replace the files inside the data folder (there is also a info textfile
to discribe wich file is for what or what files can be exist to be automaticly be used).

The Game is just written using notepad++ as long with some tips by AI (o1-model).

Graphics are created using Stable Diffusion Forge WebUI as long with the layer diffusion
extension.

Songs / Music was written by me already in in the years 1990-1993 using protracker on the
Amiga Computer (later released to AmiNet https://aminet.net/search?query=hardraver).

Have fun :-)

Source: https://github.com/zeittresor/pygame_mizzz_pongle

History

24.01.2025 v1.2
- Background swapping for each level added
- 27 new level backgrounds added
- Options menu added with sliders for music and background brightness
- "p" Key added to pause the game
- Bugfixes
- New Win32 binary release added

20.01.2025 v1.1
- Added Button "Orgon Akkumulator" to let you change the Wind direction / speed randomly every 30 seconds
- Added Button "Repulsine" to let you change the power up / ball speed every 20 seconds if last wall bumping contact was upside or downside (not left or right side)
- Added better readme.txt generation with descriptions inside the data folder for "possible available" files
- Added Commandline Options like -nospoon (no extra buttons) and -funds (max. balls 999)

  Possible files and what they are used for:
  
  - background.png: The background image used for the game.
  - bumper.png: The image of a bumper.
  - hole.png: The image of a hole at the bottom.
  - corner.png: A decorative image to be placed between the holes.
  - ball.png: The ball image.
  - bumper.wav: Sound effect for bumpers.
  - border.wav: Sound effect when ball hits the border.
  - panel.wav: Sound effect for the flippers.
  - button.wav: Sound effect when clicking on the buttons.
  - panel_left.png: Custom image for the left flipper.
  - panel_right.png: Custom image for the right flipper.
  - orgon.png: Custom image for the Orgon Accumulator button.
  - repulsine.png: Custom image for the Repulsine button.
  - Any .mp3 file: Will be played as background music.

  
Command line parameters:

-debuglog : prints debug messages.
-nospoon : disables the additional buttons (Orgon Accumulator / Repulsine).
-funds : raises the number of shots to 999.
-fullscreen or other pygame flags (optional, if you modify the code accordingly).


18.01.2025 v1.0
- First release Version as source and binary for Windows
