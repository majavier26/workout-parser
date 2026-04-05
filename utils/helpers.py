import re
from .constants import WEIGHT_UNITS, SUPERSET_DELIM, DROPSET_DELIM, NOTE_DELIM, NOTE_MARKER

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

def convert_notes_to_dict(notes):
    # Initialize result dict
    result_dict = {}

    # Iterate over each note
    for note in notes:
        # Check if note contains a hyphen
        if NOTE_DELIM in note:
            # Split note into key and value
            key, value = note.split(NOTE_DELIM, 1)
            # Clean key and value by stripping whitespace
            key = key.strip()
            value = value.strip()
            # Add to result dict
            result_dict[key] = value

    return result_dict

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

def is_set_unit(text):
    # Check if there is no dropset delimiter in text
    return DROPSET_DELIM not in text

def does_set_have_notes(text):
    # Check if there is a note marker in the text
    return NOTE_MARKER in text

def get_set_notes(text, note_dict):
    # Get all instances of the note marker
    note_indices = re.findall(rf'\{NOTE_MARKER}', text)
    note_index = ''.join(note_indices)
    # Get the note text
    note_text = note_dict.get(note_index, None)

    return note_text

def get_remark_from_rep(text):
    # Get the match
    match = re.search(r'\d+', text)

    # Get the value and the remark
    value = int(match.group()) 
    remark = text[match.end():].strip()

    return value, remark