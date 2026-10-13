form Experimental HNR v1
    sentence Input_file
    real Interval_start
    real Interval_end
    positive Time_step
    positive Minimum_pitch
    real Silence_threshold
    positive Periods_per_window
endform
Read from file: input_file$
To Harmonicity (cc): time_step, minimum_pitch, silence_threshold, periods_per_window
mean = Get mean: interval_start, interval_end
mean$ = "null"
if mean <> undefined
    mean$ = fixed$(mean, 17)
endif
n = Get number of frames
step = Get time step
first_center = Get time from frame number: 1
inside = 0
valid = 0
for i from 1 to n
    t = Get time from frame number: i
    if t >= interval_start and t <= interval_end
        inside += 1
        v = Get value in frame: i
        if v <> undefined and v <> -200
            valid += 1
        endif
    endif
endfor
writeInfo: "{""hnr_mean_db"":", mean$, ",""object_frames"":", n, ",""time_step_s"":", fixed$(step, 17), ",""first_frame_center_s"":", fixed$(first_center, 17), ",""total_frames"":", inside, ",""valid_frames"":", valid, ",""frames"": ["
separator$ = ""
for i from 1 to n
    t = Get time from frame number: i
    if t >= interval_start and t <= interval_end
        v = Get value in frame: i
        v$ = "null"
        if v <> undefined
            v$ = fixed$(v, 17)
        endif
        appendInfo: separator$, "{""frame_index"":", i, ",""time_s"":", fixed$(t, 17), ",""praat_raw_hnr_db"":", v$, "}"
        separator$ = ","
    endif
endfor
appendInfoLine: "]}"
