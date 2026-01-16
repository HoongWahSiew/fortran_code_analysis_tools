import re
import os
import pandas as pd
import argparse
import sys

def generate_fortran_matrix(directory):
    # 1. Setup Regex Patterns
    # Find start/end of routines to track scope
    routine_start = re.compile(r'^\s*(?:recursive\s+)?(?:subroutine|function)\s+(\w+)', re.IGNORECASE)
    routine_end = re.compile(r'^\s*end\s+(?:subroutine|function)', re.IGNORECASE)
    call_pattern = re.compile(r'(?:call\s+|(?<=\W))(\w+)\s*\(', re.IGNORECASE)

    all_routines = {} # {routine_name: [list_of_calls]}
    
    # 2. First pass: Find all routine names (The "Universe")
    for filename in os.listdir(directory):
        if filename.endswith(".f90"):
            with open(os.path.join(directory, filename), 'r') as f:
                content = f.read()
                # Join line continuations (&)
                content = re.sub(r'&\s*\n\s*', '', content)
                
                lines = content.splitlines()
                current_routine = None
                
                for line in lines:
                    start_match = routine_start.match(line)
                    if start_match:
                        current_routine = start_match.group(1).lower()
                        all_routines[current_routine] = []
                    elif routine_end.match(line):
                        current_routine = None
                    
                    # If we are inside a routine, look for calls
                    if current_routine:
                        # Find all words followed by '(' or preceded by 'call'
                        found_calls = call_pattern.findall(line)
                        for call in found_calls:
                            call = call.lower()
                            if call != current_routine: # Ignore self-recursion for now
                                all_routines[current_routine].append(call)

    # 3. Filter calls: Only keep calls that exist in our "Universe"
    universe = sorted(list(all_routines.keys()))
    
    # 4. Initialize the Matrix with 0s
    # Columns = Caller (i), Rows = Callee (j)
    matrix = pd.DataFrame(0, index=universe, columns=universe)

    # 5. Fill the Matrix
    for caller, callees in all_routines.items():
        for callee in callees:
            if callee in universe:
                # Per your request: Looking at column 'i' shows what 'i' called
                # So: matrix.loc[callee, caller] = 1
                matrix.at[callee, caller] = 1

    return matrix


if __name__ == "__main__":
    # Setup command line argument parsing
    parser = argparse.ArgumentParser(description="Generate a dependency matrix for Fortran source files.")
    parser.add_argument("dir", nargs="?", default=".", help="The directory containing .f90 files (default: current directory)")
    parser.add_argument("--csv", action="store_true", help="Save the output to dependency_matrix.csv")
    
    args = parser.parse_args()

    result_matrix = generate_fortran_matrix(args.dir)

    if result_matrix is not None:
        print(f"\nDependency Matrix for: {os.path.abspath(args.dir)}")
        print(f"Note: Columns are 'Callers', Rows are 'Callees'\n")
        print(result_matrix)

        if args.csv:
            result_matrix.to_csv("dependency_matrix.csv")
            print("\nMatrix saved to 'dependency_matrix.csv'")