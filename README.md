# StatTrack
StatTrack is a Python application designed to visualize and analyze challenge scores over time in Kovaak's. It provides features to load, filter, and plot challenge data from a specified directory. The application also supports custom sets of challenges, points of interest, and contains presets for Season 4 and 5 Voltaic Benchmarks.

I wanted to be able to see how my scores improved overall on one graph, so I built this over the last few days. If the code is jank it's because it is. Lotta AI code in here but thats the future I guess.

Usage
1. Select Stats Folder: Click the "Select Stats Folder" button to choose the directory containing stat sheets.
2. Filter Challenges: Use the search bar to filter challenges by name.
3. Select Challenges: Select challenges from the listbox to plot their scores. You can select as many as you would like to plot.
4. Voltaic Benchmarks: Use the Voltaic Benchmarks menu to select challenges by season and difficulty.
5. Custom Sets: Use the Custom Sets menu to create, modify, or delete custom challenge sets.
6. Points of Interest: Add or delete points of interest to mark significant events on the plot. I made this so I can mark significant changes in my setup (ie new mousepad)
7. Plot Options: Check the boxes for normalization, PBs, and aggregation as needed.
    - PBs graphs only your PBs as time goes on (duh) which is great for seeing long term progress.
    - Normalization is useful for graphing multiple tasks at once with large variances in score systems (ex: PB of 76 vs Pb of 3200).
    - Aggregation converts all selected graphs into one line. This is best with Pbs and Normalization selected. This allows me to see how I have been improving on a large set of tasks with one simple line.
8. Plot Scores: Click the "Plot Scores" button to generate the plot based on the selected challenges and options.