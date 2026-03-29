import re

# Workout log > Movement > Set > Subset > Load + Rep

#################################
# VARIABLES
#################################

WEIGHT_UNITS = ['kg', 'lbs', 'bar', 'caret', 'BW']
SUPERSET_DELIM = '/'
DROPSET_DELIM = '>'
RESTPAUSE_DELIMS = ['no rest', '...', '..']
HAND_REP_DELIM = '~'

#################################
# WORKOUT LOG
#################################

def group_log_by_content(text):
    # Split string by new lines
    result = text.split('\n')

    # Initialize storage for exercises, notes, comments, weight
    result_dict = {
        'exercises': [],
        'notes': [],
        'comments': [],
        'weight': []
    }
    
    # Initialize key to append to
    key = None
    # Iterate through each line and group by content
    for line in result:
        # Check if line is empty
        if line.strip() == '':
            key = None
            continue

        # Check first if its the comments
        if line.startswith('Comments:'):
            key = 'comments'
            continue

        # Check if line is a note
        if line.startswith('Notes:'):
            key = 'notes'
            continue

        # Check if line is a weight entry
        if line.startswith('Weight'):
            delimiters = [' - ', ': ']
            for delimiter in delimiters:
                if delimiter in line:
                    weight = line.split(delimiter)[1]
                    result_dict['weight'].append(weight)
            continue
          
        # Append
        if key is not None:
            result_dict[key].append(line)
        else:
            result_dict['exercises'].append(line)

    return result_dict

def parse_workout_log(text):
    # Group the log by content
    grouped_log = group_log_by_content(text)

    # Parse exercises
    exercises = []
    for exercise in grouped_log['exercises']:
        print(f'Parsing exercise: {exercise}')
        exercises.append(parse_exercise(exercise))

    return {
        'exercises': exercises,
        'notes': grouped_log.get('notes', []),
        'comments': grouped_log.get('comments', []),
        'weight': grouped_log.get('weight', [])
    }

def sanitize_exercise(text):
    # Strip tally marks (trailing slashes)
    text = re.sub(r'\s*/+\s*$', '', text)

    # Strip (skip) markers
    text = re.sub(r'\s*\(skip\)\s*', '', text)

    # Expand NxR shorthand
    def expand_nx(match):
        n = int(match.group(1))
        r = match.group(2)
        return ', '.join([r] * n)

    # Make the weight unit union pattern
    WEIGHT_UNITS_PATTERN = '|'.join(WEIGHT_UNITS)
    # Search for nxr patterns and replace them accordingly but not for weights
    text = re.sub(
        rf'(?<!\+)(\d+)x(\d+)(?!\s*(?:{WEIGHT_UNITS_PATTERN}))', 
        expand_nx, 
        text
    )

    # Fix stray ", F" → append F to previous rep
    text = re.sub(r'(\d),\s*F\b', r'\1F', text)

    return text

#################################
# EXERCISE
#################################

def separate_name_from_movements(text):
    # Get the name by splitting by hyphen
    name, movements = text.split(' - ', 1)
    # Clean name by whitespace
    name = name.strip()

    return name, movements

def get_exercise_id(name):
    # Make id
    id = name.lower().replace(' ', '_')

    return id

def convert_superset_to_sets(text):
    # Separate name from movements
    name, movements = separate_name_from_movements(text)

    # Split name by delimiter
    name_list = [n.strip() for n in name.split(SUPERSET_DELIM)]
    # Split movements by comma
    movement_list = re.split(r',\s*', movements)

    # Initialize result list
    result_list = [f'{name} -' for name in name_list]
    # Iterate over each movement
    for movement in movement_list:
        # Separate load from reps
        load, rep = separate_load_from_rep(movement)
        # Separate the load and rep by superset delimiter
        load_list = [l.strip() for l in load.split(SUPERSET_DELIM)]
        rep_list = [r.strip() for r in rep.split(SUPERSET_DELIM)]

        # Append the load and rep to the corresponding exercise string in the result list
        for idx, (l, r) in enumerate(zip(load_list, rep_list)):
            result_list[idx] += f' {l} {r},'

    # Clean trailing commas
    result_list = [s.rstrip(',') for s in result_list]

    return result_list

def parse_exercise(text):
    # Initialize storage
    result_dict = {
        'id': None,
        'movements': []
    }

    # Convert superset to sets if there is a superset delimiter in the text
    if SUPERSET_DELIM in text:
        exercise_list = convert_superset_to_sets(text)
    else:
        exercise_list = [text]

    # Build the id from all movement names
    names = [separate_name_from_movements(e)[0] for e in exercise_list]
    result_dict['id'] = '_'.join(get_exercise_id(n) for n in names) + '_set'

    for exercise_idx, exercise in enumerate(exercise_list):
        # Get the name by splitting by hyphen
        name, movements = separate_name_from_movements(exercise)

        # Add movement name and sets
        movement_dict = {'name': name, 'sets': []}
        result_dict['movements'].append(movement_dict)

        # Get all sets
        sets = re.split(r',\s*', movements) # split by comma and space(s)
        # Initialize previous load
        previous_load = None
        # Iterate over each set and parse it
        for set_text in sets:
            # Separate load from rep
            load, rep = separate_load_from_rep(text)
            if load is None:
                load = previous_load
            else:
                previous_load = load

            # Parse the set and append to movement
            result_dict['movements'][exercise_idx]['sets'].append(parse_set(load, rep))

    return result_dict

#################################
# MOVEMENT
#################################

def parse_movement(text):
    """
    Separatea a movement 
    """
    # Split text by comma and any number of whitespaces
    sets = re.split(r',\s*', text)

    return sets

def find_rightmost_weight(text):
    # Initialize index and units of weight
    weight_index = -1
    rightmost_weight = None

    for weight_unit in WEIGHT_UNITS:
            print(f'Looking for {weight_unit}')
            # Find the weight unit
            found_index = text.rfind(weight_unit)

            # Update weight index if it's the rightmost weight unit
            if found_index > weight_index:
                print(f'Found {weight_unit} at {found_index}')
                weight_index = found_index
                rightmost_weight = weight_unit

    print(f'Rightmost weight unit is {rightmost_weight} at {weight_index}')

    return weight_index, rightmost_weight

def separate_load_from_rep(text):
    # Get index of rightmost weight
    weight_index, rightmost_weight = find_rightmost_weight(text)

    # Early return if no weight index
    if weight_index == -1:
        return None, text

    # Initialize boundary accounting for length of unit
    boundary_index = weight_index + len(rightmost_weight)
    # Check for the actual boundary between load and rep
    for t in text[boundary_index:]:
        try: 
            # Convert character to integer
            int(t)
            # Increment boundary index
            boundary_index += 1
        except:
            break

    # Separate load from rep
    load = text[:boundary_index].strip()
    rep = text[boundary_index:].strip()
    
    return load, rep

#################################
# SET
#################################

def is_set_unit(text):
    # Check if there is no dropset delimiter in text
    return DROPSET_DELIM not in text

def parse_set(load, rep):
    is_unit_set = is_set_unit(rep)

    # Initialize storage
    result = {}

    # Add loads and reps to result
    result['kind'] = 'unit' if is_unit_set else 'drop'
    result['subsets'] = {}

    # Add load to subset if drop set or not
    result['subsets']['load'] = load
    result['subsets']['reps'] = parse_subset(rep) if is_unit_set else parse_dropset(rep)

    return result

#################################
# SUBSET
#################################

def parse_subset_hand(text):
    # Split left and right rep
    left_rep, right_rep = text.split(HAND_REP_DELIM)

    return {
        'left': left_rep,
        'right': right_rep
    }

def parse_subset(text):
    # Check for rest-pause
    for delim in RESTPAUSE_DELIMS:
        if delim in text:
            parts = [p.strip() for p in text.split(delim)]
            return [parse_subset(part) for part in parts]  # recursive
    
    # Check if set is separated by hand
    if HAND_REP_DELIM in text:
        return parse_subset_hand(text)
    
    # Try to encode it now
    try:
        return int(text)
    except:
        # Return as string if there are remarks (e.g. "4F", "10 NROM")
        return text

def parse_dropset(text):
    # Initialize separated dropsets
    result = []
    # Split load and rep 
    load, rep = separate_load_from_rep(text)

    # Separate the loads and reps by dropset delimiter
    loads = [l.strip() for l in load.split(DROPSET_DELIM)]
    reps = [r.strip() for r in rep.split(DROPSET_DELIM)]

    # Pair each load and rep
    for load, rep in zip(loads, reps):
        result.append({
            'load': load,
            'reps': parse_subset(rep)
        })

    return result

def parse_restpause_in_subset(text):
    # Initialize separated dropsets
    result = []
    # Iterate over all subsets
    for restpause_delim in RESTPAUSE_DELIMS:
        if restpause_delim in text:
            # Split text by rest/pause identifier
            result = text.split(restpause_delim)
            # Strip all text
            result = [subset.strip() for subset in result]

        # Parse each subset individually if there are left and right-specific rep
        result = [parse_subset(subset) for subset in result]

    return result