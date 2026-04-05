import re
from .constants import (
    SUPERSET_DELIM, DROPSET_DELIM, HAND_REP_DELIM, RESTPAUSE_DELIMS, NOTE_MARKER
)
from .helpers import (
    convert_notes_to_dict, does_set_have_notes,
    get_remark_from_rep, get_set_notes,
    convert_superset_to_sets, separate_load_from_rep, 
    group_log_by_content, sanitize_exercise, is_set_unit, 
    separate_name_from_movements, get_exercise_id
)

class WorkoutParser:
    """
    The workout parser takes in a workout log and parses it into a structured format. 

    The hierarchy of the workout log is as follows:
        Workout log > Movement > Set > Subset > Load + Rep

    The structure is as follows:
        {
            "exercises": List[Exercise],
            "comments": List[str],
            "metrics": dict[str, str | int | float]
        }
    """
    def __init__(self, text): 
        self.text = text
        self.workout_dict = group_log_by_content(self.text)
        self.exercises = self.workout_dict.get('exercises', [])
        self.comments = self.workout_dict.get('comments', [])
        self.notes = self.workout_dict.get('notes', [])
        self.note_dict = convert_notes_to_dict(self.notes)
        self.metrics = self.workout_dict.get('metrics', {})

    def __repr__(self):
        return f"""
         WorkoutParser(
            text={self.text},
            exercises={self.exercises},
            comments={self.comments},
            notes={self.notes},
            metrics={self.metrics})
        )
        """

    #################################
    # METHODS
    #################################

    def parse_workout_log(self):
        """
        Parse the workout log into a structured format.
        Orchestrates the parsing of the workout log.
        Entry point for parsing the workout log.
        """

        # Parse exercises
        exercises = []
        for exercise in self.exercises:
            print(f'Parsing exercise: {exercise}')
            exercises.append(self.parse_exercise(exercise))

        return {
            'exercises': exercises,
            'notes': self.notes,
            'comments': self.comments,
            'weight': self.workout_dict.get('weight', [])
        }
    
    #################################
    # EXERCISE
    #################################

    def parse_exercise(self, text):
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
            # Clean the exercise
            exercise = sanitize_exercise(exercise)
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
                load, rep = separate_load_from_rep(set_text)
                if load is None:
                    load = previous_load
                else:
                    previous_load = load

                # Parse the set and append to movement
                result_dict['movements'][exercise_idx]['sets'].append(self.parse_set(load, rep))

        return result_dict

    #################################
    # SET
    #################################

    def parse_set(self, load, rep):
        is_unit_set = is_set_unit(rep)

        # Initialize storage
        result = {}

        # Add loads and reps to result
        result['kind'] = 'unit' if is_unit_set else 'drop'

        # Add load to subset if drop set or not
        if is_unit_set:
            result['subsets'] = {
                'load': load,
                'reps': self.parse_subset(rep)
            }
        else:
            result['subsets'] = self.parse_dropset(load, rep)

        return result

    #################################
    # SUBSET
    #################################

    def parse_subset_hand(self, text):
        # Split left and right rep
        left_rep, right_rep = text.split(HAND_REP_DELIM)

        return {
            'left': self.parse_subset(left_rep),
            'right': self.parse_subset(right_rep)
        }

    def parse_subset(self, text):
        # Check for rest-pause
        for delim in RESTPAUSE_DELIMS:
            if delim in text:
                parts = [p.strip() for p in text.split(delim)]
                return [self.parse_subset(part) for part in parts]  # recursive part
        
        # Check if set is separated by hand
        if HAND_REP_DELIM in text:
            return self.parse_subset_hand(text)
        
        # Initialize note text
        note_text = None
        # Check for notes
        if does_set_have_notes(text):
            # Get the notes
            note_text = get_set_notes(text, self.note_dict)
            # Remove the note marker from the text
            text = text.replace(NOTE_MARKER, '').strip()

        # Get the value and the remark
        value, remark = get_remark_from_rep(text)
        
        # Encode the subset
        subset_dict = { 'value': value }
        # Add the remark if it exists
        if remark:
            subset_dict['remark'] = remark
        # Add the note if it exists
        if note_text is not None:
            subset_dict['note'] = note_text

        return subset_dict

    def parse_dropset(self, load, rep):
        # Initialize separated dropsets
        result = []

        # Separate the loads and reps by dropset delimiter
        loads = [l.strip() for l in load.split(DROPSET_DELIM)]
        reps = [r.strip() for r in rep.split(DROPSET_DELIM)]

        # Pair each load and rep
        for load, rep in zip(loads, reps):
            result.append({
                'load': load,
                'reps': self.parse_subset(rep)
            })

        return result