# Useful SQL and Bash Commands

## Checking status on phases 1 and 2

List the render stage files we've downloaded, organized by their prompt
```
select * from render_stage ORDER by prompt_id;
```

Get high level info on the prompts, like how many times we've queried stages
```
select id, channel_id, message_id, author_username, is_abandoned, n_tries from prompt;
```
Get more high level info on the prompt, including how many stages it has
```
select prompt.id, channel_id, message_id, author_username, is_abandoned, n_tries, count(render_stage.id) as num_stages from prompt JOIN render_stage on render_stage.prompt_id = prompt.id GROUP BY render_stage.prompt_id;
```
A slightly better sql command that treats zeros propery
```
select prompt.id, channel_id, message_id, author_username, is_abandoned, n_tries, count(render_stage.id) as num_stages from prompt LEFT OUTER JOIN render_stage on render_stage.prompt_id = prompt.id GROUP BY prompt.id;
```
An even better command that also tells us if phase01 has found the url for the final image
```
select prompt.id, render_id, final_url is not NULL AS finished, channel_id, message_id, author_username, is_abandoned, n_tries, count(render_stage.id) as num_stages from prompt LEFT OUTER JOIN render_stage on render_stage.prompt_id = prompt.id GROUP BY prompt.id;
```


## Checking status on phase03 and phase04
Check on which videos are in the pool of things that phase03 has created
```mysql
select id, author_username from prompt where local_video_path IS NOT NULL LIMIT 100;
```
```bash
ls outdir/prompt_*
```

Check what videos have gone our recently (or ever)
```mysql
select * from render_output_event;
```

Check if there have there been duplicates that have gone our recently.  
Option 1:
```mysql
select count(id) from render_output_event GROUP BY prompt_id;
```
Option 2:
```mysql
select n_dupes from (select count(id) as n_dupes from render_output_event GROUP BY prompt_id) as temptable WHERE n_dupes > 1;
```
Option 3:
Similar to option1, but shows organizes by what has happened recently
```mysql
select prompt_id, count(id), min(timestamp), max(timestamp) from render_output_event GROUP BY prompt_id order by timestamp desc limit 100;
```


## Checking metatdata on prompts and output

A command to ask how many stages (min, max, average) we usually get from a prompt)
```
SELECT avg(num_stages), min(num_stages), max(num_stages) from (select prompt.id, render_id, final_url is not NULL AS finished, channel_id, message_id, final_message_id, author_username, is_abandoned, n_tries, count(ren
der_stage.id) as num_stages from prompt LEFT OUTER JOIN render_stage on render_stage.prompt_id = prompt.id WHERE final_url is not NULL GROUP BY prompt.id) AS table1;
```

Compute the min, average, max amount of time from when a video is requested by the user to when it is scheduled to stream (add previous video duration to get the approx total latency).
```mysql
select min(td), sec_to_time(avg(time_to_sec(td))), max(td) from (select prompt_id, timediff(render_output_event.timestamp, prompt.timestamp) as td from prompt LEFT JOIN render_output_event ON prompt.id = render_output_event.prompt_id where render_output_event.timestamp IS NOT NULL and final_url IS NOT NULL) as table1;
```

Check how many videos have been streamed a certin number of times. The "times" filter on the end can be set to 0, 1, 2, 3, 4, 5, etc
```mysql
select * from (select prompt.id, render_output_event.prompt_id, count(render_output_event.id) as times from prompt left join render_output_event on prompt.id = prompt_id group by prompt.id) as table1 where times = 0;
```


## Setting and resetting tests

Delete all the videos that are "ready to go out" (resetting phase03)
```mysql:
update prompt set local_video_path=NULL where local_video_path IS NOT NULL;
```
```bash:
rm outdir/prompt_*_output.mp4
```

Delete the history of all videos that have gone out (resetting phase04). Note you can set the id threshold to delete less than everything
```mysql
delete from render_output_event where id < 0;
```

