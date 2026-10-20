form Independent concordance oracle; different script/process
 sentence Input_pitch
endform
Read from file: input_pitch$
count = Get number of frames
valid = 0
for frame from 1 to count
 f = Get value in frame: frame, "Hertz"
 if f <> undefined
  valid += 1
 endif
endfor
lo = Get minimum: 0, 0, "Hertz", "None"
hi = Get maximum: 0, 0, "Hertz", "None"
q90 = Get quantile: 0, 0, 0.90, "Hertz"
q10 = Get quantile: 0, 0, 0.10, "Hertz"
q50 = Get quantile: 0, 0, 0.50, "Hertz"
sigmaST = Get standard deviation: 0, 0, "semitones"
sigma = Get standard deviation: 0, 0, "Hertz"
mu = Get mean: 0, 0, "Hertz"
writeInfoLine: mu, tab$, q50, tab$, sigma, tab$, sigmaST, tab$, q10, tab$, q90, tab$, lo, tab$, hi, tab$, count, tab$, valid
