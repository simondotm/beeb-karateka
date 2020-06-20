Process the frames in chunks (can be say 24 at a time)
Load each frame, scale down to 160x90 (or a squashed version)
Append each frame side by side to make one wide image
Pngquant the wide image to compute an optimal palette for the chunk
(save out all of the chunked frames individually for debugging purposes)
EOR each frame with the last frame in the chunk.

export chunk header
 palette
 number of frames
 For each frame:
  convert to bbc micro format
   Run lengths of 0, followed by run lengths of non zero.
write chunk
concatenate all chunks
exo compress the lot with a big buffer size
hope it fits into 400Kb!

when unpacking, use double buffering and duplicate to double height
try and use streaming