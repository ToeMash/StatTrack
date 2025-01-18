import os
import pandas as pd
import matplotlib.pyplot as plt
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, Menu, simpledialog, Toplevel, Listbox, Button, END, Entry
import json
from collections import Counter

def load_voltaic_challenges(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def load_custom_sets(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return {}

def save_custom_sets(filename, custom_sets):
    with open(filename, 'w') as file:
        json.dump(custom_sets, file)

def load_points_of_interest(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            return json.load(file)
    return []

def save_points_of_interest(filename, points_of_interest):
    with open(filename, 'w') as file:
        json.dump(points_of_interest, file)

# Load the challenges from the JSON file
voltaic_challenges = load_voltaic_challenges('voltaic_challenges.json')

# Load points of interest
points_of_interest = load_points_of_interest('points_of_interest.json')

def parse_stat_sheet(file_path):
    with open(file_path, 'r') as file:
        data = file.read()

    # Extract challenge start time, scenario, and score
    challenge_start_match = re.search(r'Challenge Start:,(.*?)\n', data)
    scenario_match = re.search(r'Scenario:,(.*?)\n', data)
    score_match = re.search(r'Score:,(.*?)\n', data)

    if not (challenge_start_match and scenario_match and score_match):
        return None, None, None

    challenge_start = challenge_start_match.group(1).strip()
    scenario = scenario_match.group(1).strip()
    score = float(score_match.group(1).strip())

    # Extract time from challenge start
    challenge_time = datetime.strptime(challenge_start, '%H:%M:%S.%f').time()

    # Use the file's modification date as the date
    modification_time = os.path.getmtime(file_path)
    challenge_date = datetime.fromtimestamp(modification_time).date()

    # Combine date and time into a single datetime object
    challenge_datetime = datetime.combine(challenge_date, challenge_time)

    return challenge_datetime, scenario, score

def collect_challenges(directory_path):
    challenge_counter = Counter()

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path):
            _, challenge, _ = parse_stat_sheet(file_path)
            if challenge:
                challenge_counter[challenge] += 1

    # Sort challenges by the number of entries, from most to fewest
    sorted_challenges = sorted(challenge_counter.items(), key=lambda item: item[1], reverse=True)
    return [challenge for challenge, count in sorted_challenges]

def plot_scores_for_challenges(directory_path, selected_challenges, show_pb=False, normalize=False, aggregate=False):
    # Create a DataFrame to store the parsed data
    data = {
        'Datetime': [],
        'Challenge': [],
        'Score': []
    }

    # Iterate over each file in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path):
            datetime_value, challenge, score = parse_stat_sheet(file_path)
            if datetime_value is not None and challenge in selected_challenges:
                data['Datetime'].append(datetime_value)
                data['Challenge'].append(challenge)
                data['Score'].append(score)

    df = pd.DataFrame(data)
    df.sort_values(by='Datetime', inplace=True)

    plt.figure(figsize=(10, 6))

    if aggregate:
        # Group by date and calculate the mean score for each date
        df['Date'] = df['Datetime'].dt.date

        if show_pb:
            # Calculate cumulative max scores within each challenge
            df['Score'] = df.groupby('Challenge')['Score'].cummax()

        if normalize:
            df['Score'] = df.groupby('Challenge')['Score'].transform(lambda x: x / x.max() if x.max() != 0 else x)

        # Calculate the mean of the scores for each date
        aggregated_scores = df.groupby('Date')['Score'].mean()

        # Apply cumulative max to the mean scores
        if show_pb:
            aggregated_scores = aggregated_scores.cummax()

        plt.plot(aggregated_scores.index, aggregated_scores.values, marker='o', label='Aggregate')

        # Draw vertical lines based on benchmark selection
        colors = plt.cm.tab10.colors  # Use a colormap with distinct colors
        color_index = 0

        if selected_pairs:
            for season, level in selected_pairs:
                benchmark_challenges = voltaic_challenges.get(season, {}).get(level, [])
                first_occurrence = df[df['Challenge'].isin(benchmark_challenges)]['Datetime'].min()
                if pd.notnull(first_occurrence):
                    plt.axvline(x=first_occurrence, color=colors[color_index % len(colors)], linestyle='--', label=f'Start {season}-{level}')
                    color_index += 1
        else:
            for challenge in selected_challenges:
                first_occurrence = df[df['Challenge'] == challenge]['Datetime'].min()
                if pd.notnull(first_occurrence):
                    plt.axvline(x=first_occurrence, color=colors[color_index % len(colors)], linestyle='--', label=f'Start {challenge}')
                    color_index += 1
    else:
        for challenge in selected_challenges:
            df_challenge = df[df['Challenge'] == challenge]

            if normalize:
                max_score = df_challenge['Score'].max()
                df_challenge.loc[:, 'Score'] = df_challenge['Score'] / max_score if max_score != 0 else df_challenge['Score']

            if show_pb:
                pb_scores = df_challenge['Score'].cummax()
                plt.plot(df_challenge['Datetime'], pb_scores, marker='o', label=f'{challenge} (PB)')
            else:
                plt.plot(df_challenge['Datetime'], df_challenge['Score'], marker='o', label=challenge)

    # Draw vertical lines for points of interest
    for poi in points_of_interest:
        poi_date = datetime.strptime(poi['date'], '%Y-%m-%d')
        plt.axvline(x=poi_date, color='red', linestyle='--', label=poi['name'])

    plt.title('Scores Over Time')
    plt.xlabel('Date and Time')
    plt.ylabel('Score' + (' (Normalized)' if normalize else ''))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.show()

def select_directory():
    directory_path = filedialog.askdirectory(title="Select Stats Folder")
    if directory_path:
        save_directory_path(directory_path)
        filepath_label.config(text=f"Selected Path: {directory_path}")
        update_challenge_list(directory_path)

def save_directory_path(directory_path):
    config = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r') as file:
            config = json.load(file)
    config['directory_path'] = directory_path
    with open('config.json', 'w') as file:
        json.dump(config, file)

def load_directory_path():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as file:
            config = json.load(file)
            return config.get('directory_path', '')
    return ''

def update_challenge_list(directory_path):
    challenges = collect_challenges(directory_path)
    global all_challenges
    all_challenges = challenges
    challenge_listbox.delete(0, tk.END)
    for challenge in challenges:
        challenge_listbox.insert(tk.END, challenge)

def filter_challenges():
    search_text = search_entry.get().lower()
    challenge_listbox.delete(0, tk.END)
    for challenge in all_challenges:
        if search_text in challenge.lower():
            challenge_listbox.insert(tk.END, challenge)

def on_plot_scores():
    directory_path = load_directory_path()
    if directory_path:
        selected_indices = challenge_listbox.curselection()
        selected_challenges = [challenge_listbox.get(i) for i in selected_indices]

        if not selected_challenges:
            messagebox.showwarning("Warning", "No challenges selected. Please select at least one challenge.")
            return

        # Get the state of the checkboxes
        show_pb = show_pb_var.get()
        normalize = normalize_var.get()
        aggregate = aggregate_var.get()

        # Plot scores for the selected challenges
        plot_scores_for_challenges(directory_path, selected_challenges, show_pb, normalize, aggregate)
    else:
        messagebox.showerror("Error", "No directory selected. Please select a directory first.")

def select_voltaic_challenge(season, level):
    # Track selected season-level pairs
    if level == "All":
        for difficulty in ["Novice", "Intermediate", "Advanced"]:
            select_voltaic_challenge(season, difficulty)
    else:
        selected_pairs.add((season, level))
        # Get challenges for the selected season and level
        selected_challenges = voltaic_challenges.get(season, {}).get(level, [])
        # Select the challenges in the listbox
        for challenge in selected_challenges:
            for i, item in enumerate(all_challenges):
                if item == challenge:
                    challenge_listbox.selection_set(i)

        # Update the selected benchmarks label
        update_selected_benchmarks_label()

def update_selected_benchmarks_label():
    # Format the selected pairs as "[Season]-[Difficulty]"
    selected_text = ', '.join([f"{season}-{level}" for season, level in selected_pairs])
    custom_sets_text = ', '.join(selected_custom_sets)

    # Combine the texts and remove any leading or trailing commas
    combined_text = ', '.join(filter(None, [selected_text, custom_sets_text]))

    selected_benchmarks_label.config(text=f"Selected Benchmarks: {combined_text}")

def clear_benchmarks():
    # Clear the selected pairs and update the UI
    selected_pairs.clear()
    selected_custom_sets.clear()
    challenge_listbox.selection_clear(0, tk.END)
    update_selected_benchmarks_label()

def on_aggregate_toggled():
    # If Aggregate is checked, also check Normalize
    if aggregate_var.get():
        normalize_var.set(True)

def add_custom_set():
    set_name = simpledialog.askstring("Input", "Enter the name of the new set:")
    if set_name:
        # Create a new window to select challenges for the custom set
        select_challenges_window = Toplevel(root)
        select_challenges_window.title(f"Select Challenges for {set_name}")

        # Frame for search bar and filter button
        search_frame = tk.Frame(select_challenges_window)
        search_frame.pack(pady=10)

        # Create a search bar
        search_entry = tk.Entry(search_frame)
        search_entry.pack(side=tk.LEFT, padx=5)

        # Create a search button
        search_button = tk.Button(search_frame, text="Filter Challenges", command=lambda: filter_custom_set_challenges(search_entry.get().lower(), challenges_listbox))
        search_button.pack(side=tk.LEFT)

        # Frame for listboxes
        listbox_frame = tk.Frame(select_challenges_window)
        listbox_frame.pack(pady=10)

        # Create a listbox to display and select challenges
        challenges_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE)
        challenges_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

        # Create a listbox to display selected challenges
        selected_challenges_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE)
        selected_challenges_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

        # Populate the listbox with challenges
        for challenge in all_challenges:
            challenges_listbox.insert(tk.END, challenge)

        def filter_custom_set_challenges(search_text, listbox):
            listbox.delete(0, tk.END)
            for challenge in all_challenges:
                if search_text in challenge.lower():
                    listbox.insert(tk.END, challenge)

        def add_to_selected():
            selected_indices = challenges_listbox.curselection()
            for i in selected_indices:
                challenge = challenges_listbox.get(i)
                if challenge not in selected_challenges_listbox.get(0, tk.END):
                    selected_challenges_listbox.insert(tk.END, challenge)

        def remove_from_selected():
            selected_indices = selected_challenges_listbox.curselection()
            for i in reversed(selected_indices):  # Iterate in reverse to avoid index shifting issues
                selected_challenges_listbox.delete(i)

        def save_custom_set():
            selected_challenges = selected_challenges_listbox.get(0, tk.END)
            custom_sets[set_name] = selected_challenges
            custom_sets_menu.add_command(label=set_name, command=lambda s=set_name: select_custom_set(s))
            save_custom_sets('custom_sets.json', custom_sets)
            select_challenges_window.destroy()

        # Button to add selected challenges to the selected listbox
        add_button = Button(select_challenges_window, text="Add to Set", command=add_to_selected)
        add_button.pack(pady=5)

        # Button to remove selected challenges from the selected listbox
        remove_button = Button(select_challenges_window, text="Remove from Set", command=remove_from_selected)
        remove_button.pack(pady=5)

        # Add a button to save the selected challenges to the custom set
        save_button = Button(select_challenges_window, text="Save Set", command=save_custom_set)
        save_button.pack(pady=5)

def select_custom_set(set_name):
    # Track selected custom sets
    selected_custom_sets.add(set_name)

    # Get challenges for the selected custom set
    selected_challenges = custom_sets.get(set_name, [])

    # Select the challenges in the listbox
    for challenge in selected_challenges:
        for i, item in enumerate(all_challenges):
            if item == challenge:
                challenge_listbox.selection_set(i)

    # Update the selected benchmarks label
    update_selected_benchmarks_label()

def modify_or_delete_custom_set():
    # Create a new window to select a set to modify or delete
    modify_delete_window = Toplevel(root)
    modify_delete_window.title("Modify or Delete Set")

    # Frame for listbox and buttons
    listbox_frame = tk.Frame(modify_delete_window)
    listbox_frame.pack(pady=10)

    # Create a listbox to display existing sets
    sets_listbox = Listbox(listbox_frame)
    sets_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

    # Populate the listbox with existing sets
    for set_name in custom_sets:
        sets_listbox.insert(tk.END, set_name)

    def modify_set():
        selected_indices = sets_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "No set selected. Please select a set to modify.")
            return
        selected_set = sets_listbox.get(selected_indices[0])
        if selected_set:
            # Create a new window to modify the selected set
            modify_set_window = Toplevel(root)
            modify_set_window.title(f"Modify Set: {selected_set}")

            # Frame for search bar and filter button
            search_frame = tk.Frame(modify_set_window)
            search_frame.pack(pady=10)

            # Create a search bar
            search_entry = tk.Entry(search_frame)
            search_entry.pack(side=tk.LEFT, padx=5)

            # Create a search button
            search_button = tk.Button(search_frame, text="Filter Challenges", command=lambda: filter_custom_set_challenges(search_entry.get().lower(), challenges_listbox))
            search_button.pack(side=tk.LEFT)

            # Frame for listboxes
            listbox_frame = tk.Frame(modify_set_window)
            listbox_frame.pack(pady=10)

            # Create a listbox to display and select challenges
            challenges_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE)
            challenges_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

            # Create a listbox to display selected challenges
            selected_challenges_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE)
            selected_challenges_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

            # Populate the listbox with challenges
            for challenge in all_challenges:
                challenges_listbox.insert(tk.END, challenge)

            # Populate the selected challenges listbox with the existing challenges in the set
            for challenge in custom_sets[selected_set]:
                selected_challenges_listbox.insert(tk.END, challenge)

            def filter_custom_set_challenges(search_text, listbox):
                listbox.delete(0, tk.END)
                for challenge in all_challenges:
                    if search_text in challenge.lower():
                        listbox.insert(tk.END, challenge)

            def add_to_selected():
                selected_indices = challenges_listbox.curselection()
                for i in selected_indices:
                    challenge = challenges_listbox.get(i)
                    if challenge not in selected_challenges_listbox.get(0, tk.END):
                        selected_challenges_listbox.insert(tk.END, challenge)

            def remove_from_selected():
                selected_indices = selected_challenges_listbox.curselection()
                for i in reversed(selected_indices):  # Iterate in reverse to avoid index shifting issues
                    selected_challenges_listbox.delete(i)

            def save_modified_set():
                selected_challenges = selected_challenges_listbox.get(0, tk.END)
                custom_sets[selected_set] = selected_challenges
                save_custom_sets('custom_sets.json', custom_sets)
                modify_set_window.destroy()
                modify_delete_window.destroy()

            # Button to add selected challenges to the selected listbox
            add_button = Button(modify_set_window, text="Add to Set", command=add_to_selected)
            add_button.pack(pady=5)

            # Button to remove selected challenges from the selected listbox
            remove_button = Button(modify_set_window, text="Remove from Set", command=remove_from_selected)
            remove_button.pack(pady=5)

            # Add a button to save the modified set
            save_button = Button(modify_set_window, text="Save Set", command=save_modified_set)
            save_button.pack(pady=5)

    def delete_set():
        selected_indices = sets_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "No set selected. Please select a set to delete.")
            return
        selected_set = sets_listbox.get(selected_indices[0])
        if selected_set:
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete the set '{selected_set}'?"):
                del custom_sets[selected_set]
                save_custom_sets('custom_sets.json', custom_sets)
                sets_listbox.delete(selected_indices[0])

    # Button to modify the selected set
    modify_button = Button(modify_delete_window, text="Modify Set", command=modify_set)
    modify_button.pack(pady=5)

    # Button to delete the selected set
    delete_button = Button(modify_delete_window, text="Delete Set", command=delete_set)
    delete_button.pack(pady=5)

def add_point_of_interest():
    name = simpledialog.askstring("Input", "Enter the name of the point of interest:")
    date = simpledialog.askstring("Input", "Enter the date (YYYY-MM-DD):")
    if name and date:
        points_of_interest.append({'name': name, 'date': date})
        save_points_of_interest('points_of_interest.json', points_of_interest)
        update_points_of_interest_listbox()

def delete_point_of_interest():
    # Create a new window to select POIs to delete
    delete_poi_window = Toplevel(root)
    delete_poi_window.title("Delete Point of Interest")

    # Frame for listbox and buttons
    listbox_frame = tk.Frame(delete_poi_window)
    listbox_frame.pack(pady=10)

    # Create a listbox to display existing POIs
    poi_listbox = Listbox(listbox_frame, selectmode=tk.MULTIPLE)
    poi_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

    # Populate the listbox with existing POIs
    for poi in points_of_interest:
        poi_listbox.insert(tk.END, f"{poi['name']} - {poi['date']}")

    def delete_selected_pois():
        selected_indices = poi_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "No point of interest selected. Please select a point of interest to delete.")
            return
        for i in reversed(selected_indices):  # Iterate in reverse to avoid index shifting issues
            points_of_interest.pop(i)
        save_points_of_interest('points_of_interest.json', points_of_interest)
        update_points_of_interest_listbox()
        delete_poi_window.destroy()

    # Button to delete selected POIs
    delete_button = Button(delete_poi_window, text="Delete Selected POIs", command=delete_selected_pois)
    delete_button.pack(pady=5)

def update_points_of_interest_listbox():
    points_of_interest_listbox.delete(0, tk.END)
    for poi in points_of_interest:
        points_of_interest_listbox.insert(tk.END, f"{poi['name']} - {poi['date']}")
    points_of_interest_listbox.config(state='disabled')  # Disable the listbox

# Create the main application window
root = tk.Tk()
root.title("Stats Plotter")

# Variable to store the state of the checkboxes
show_pb_var = tk.BooleanVar()
normalize_var = tk.BooleanVar()
aggregate_var = tk.BooleanVar()

# Create a button to select the directory
select_button = tk.Button(root, text="Select Stats Folder", command=select_directory)
select_button.pack(pady=10)

# Label to display the selected directory path
filepath_label = tk.Label(root, text="Selected Path: None")
filepath_label.pack(pady=5)

# Frame for search bar, filter button, and Voltaic Benchmarks menu
search_frame = tk.Frame(root)
search_frame.pack(pady=10)

# Create a search bar
search_entry = tk.Entry(search_frame)
search_entry.pack(side=tk.LEFT, padx=5)

# Create a search button
search_button = tk.Button(search_frame, text="Filter Challenges", command=filter_challenges)
search_button.pack(side=tk.LEFT)

# Create a menu button for Voltaic selections
menu_button = tk.Menubutton(search_frame, text="Voltaic Benchmarks", relief=tk.RAISED)
menu = Menu(menu_button, tearoff=0)
menu_button.config(menu=menu)

# Add Seasons and Levels to the menu
for season in ["Season 4", "Season 5"]:
    submenu = Menu(menu, tearoff=0)
    for level in ["Novice", "Intermediate", "Advanced", "All"]:
        submenu.add_command(label=level, command=lambda s=season, l=level: select_voltaic_challenge(s, l))
    menu.add_cascade(label=season, menu=submenu)

menu_button.pack(side=tk.LEFT, padx=5)

# Create a menu button for Custom Sets
custom_sets_menu_button = tk.Menubutton(search_frame, text="Custom Sets", relief=tk.RAISED)
custom_sets_menu = Menu(custom_sets_menu_button, tearoff=0)
custom_sets_menu_button.config(menu=custom_sets_menu)

# Add an option to add a new set
custom_sets_menu.add_command(label="Add Set", command=add_custom_set)
custom_sets_menu.add_command(label="Modify or Delete Set", command=modify_or_delete_custom_set)
custom_sets_menu_button.pack(side=tk.LEFT, padx=5)

# Button to clear selected benchmarks
clear_button = tk.Button(search_frame, text="Clear Benchmarks", command=clear_benchmarks)
clear_button.pack(side=tk.LEFT, padx=5)

# Label to display selected benchmarks below the benchmarks button
selected_benchmarks_label = tk.Label(root, text="Selected Benchmarks: None")
selected_benchmarks_label.pack(pady=5)

# Create a listbox to display challenges
challenge_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, height=10)
challenge_listbox.pack(pady=10, fill=tk.BOTH, expand=True)

# Set to store selected season-level pairs
selected_pairs = set()

# Dictionary to store custom sets and their challenges
custom_sets = load_custom_sets('custom_sets.json')

# Populate the custom sets menu with existing sets
for set_name in custom_sets:
    custom_sets_menu.add_command(label=set_name, command=lambda s=set_name: select_custom_set(s))

# Set to store selected custom sets
selected_custom_sets = set()

# Load and display the previously selected directory path if available
initial_directory_path = load_directory_path()
if initial_directory_path:
    filepath_label.config(text=f"Selected Path: {initial_directory_path}")
    update_challenge_list(initial_directory_path)

# Create checkboxes to toggle Personal Best graph, Normalize graph, and Aggregate graph
checkbox_frame = tk.Frame(root)
checkbox_frame.pack(pady=10)

show_pb_checkbox = tk.Checkbutton(checkbox_frame, text="Graph Personal Bests", variable=show_pb_var)
show_pb_checkbox.pack(side=tk.LEFT, padx=5)

normalize_checkbox = tk.Checkbutton(checkbox_frame, text="Normalize", variable=normalize_var)
normalize_checkbox.pack(side=tk.LEFT, padx=5)

aggregate_checkbox = tk.Checkbutton(checkbox_frame, text="Aggregate", variable=aggregate_var, command=on_aggregate_toggled)
aggregate_checkbox.pack(side=tk.LEFT, padx=5)

# Create a button to plot the scores
plot_button = tk.Button(root, text="Plot Scores", command=on_plot_scores)
plot_button.pack(pady=10)

# Frame for Points of Interest
poi_frame = tk.Frame(root)
poi_frame.pack(pady=10)

# Create a listbox to display points of interest
points_of_interest_listbox = Listbox(poi_frame, selectmode=tk.MULTIPLE, height=5)
points_of_interest_listbox.pack(side=tk.LEFT, padx=5, pady=10, fill=tk.BOTH, expand=True)

# Button to add a new point of interest
add_poi_button = tk.Button(poi_frame, text="Add Point of Interest", command=add_point_of_interest)
add_poi_button.pack(side=tk.LEFT, padx=5, pady=10)

# Button to delete selected points of interest
delete_poi_button = tk.Button(poi_frame, text="Delete Point of Interest", command=delete_point_of_interest)
delete_poi_button.pack(side=tk.LEFT, padx=5, pady=10)

# Update the points of interest listbox
update_points_of_interest_listbox()

# Run the main event loop
root.mainloop()