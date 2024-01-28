# Todo list

## Deployment
- Package python code into a module
- Package all code into an rpm

# Infra
- Setup grafana and metrics
- Setup logfiles that rotate

## Code Improvements
- Right now we rely on (1) the filesystem, (2) that phase01, phase02, and phase 03 share a filesystem, and (3) that phase03 and phase04 hare a filesystem. It would be cool to modify the scripts so all "files" like images and videos are stored in a blob store (even mysql) for a few reasons. (1) these scripts dont need to run on the same machine (or container). (2) the scripts would be resistent to filesystem corruption. (3) I could backup my mysql database and know every bit of state is backed up. (4) it would be easier to write cleanup scripts because they would just need to modify mysql only. The downsides would be adding one more place scripts could fail and performance overhead of copying files over the the database
- There needs to be a fix for prompts that extend beyond the bottom of the screen. Right now they just get truncated and the user can see them getting cut off. I should either shrink the font when the prompt is so long. Or cut it off with an elipse (...) at some point (like half the screen).

## Reliability improvements
- I need to do testing and add error checking for cases when the local filesystem is full. Ideally that error checking would trigger an automatic cleaning
- I've tested that phase01 and phase02 are resistant to network outages. I should do the same checking for phase03 and phase04

## Unpatched crash bugs
- I have a few reports of phase03 crashing at the `resize_file_in_place` function call. It fails with `PIL.UnidentifiedImageError: cannot identify image file 'workdir/prompt_92315/final_image.webp' or a different prompt. I believe the root cause is that when using ffmpeg to convert things to webp it is either producing a corrupt file or no file at all. The resolution will be to add some error handling similar to what I did for final images that fail to download so it will just skip this file and move on. It looks like this only happens intermittently because it only happened 3 times (for prompt_id 92314, then 92315, then 92314 again). This didn't cause a repeated crash and eventually those videos did get rendered and streamed, so this isn't important to look into right now
