import re
import os
import pandas as pd
import argparse

def scan_fortran_directory(directory):
    # Regex patterns
    # 1. Finds the Module name
    module_pattern = re.compile(r'^\s*module\s+(\w+)', re.IGNORECASE)
    # 2. Finds Subroutines and Functions (handles optional 'recursive' prefix)
    routine_pattern = re.compile(r'^\s*(?:recursive\s+)?(subroutine|function)\s+(\w+)', re.IGNORECASE)
    
    inventory = []

    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return pd.DataFrame()

    for filename in os.listdir(directory):
        if filename.endswith((".f90", ".F90", ".f95")):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r') as f:
                # Join lines split by '&' to handle multi-line definitions
                content = f.read()
                clean_content = re.sub(r'&\s*\n\s*', '', content)
                lines = clean_content.splitlines()
                
                current_module = "External"
                
                for line in lines:
                    # Identify if we are inside a module
                    mod_match = module_pattern.match(line)
                    if mod_match:
                        current_module = mod_match.group(1).lower()
                    
                    # Identify subroutine or function
                    routine_match = routine_pattern.match(line)
                    if routine_match:
                        rtype = routine_match.group(1).lower()
                        rname = routine_match.group(2).lower()
                        
                        inventory.append({
                            "obj_name": rname,
                            "module_name": current_module,
                            "type": rtype
                        })

    return pd.DataFrame(inventory)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automate Fortran routine inventory.")
    parser.add_argument("dir", nargs="?", default=".", help="Directory to scan")
    args = parser.parse_args()

    df = scan_fortran_directory(args.dir)

    if not df.empty:
        # Organize the data
        df = df.sort_values(by=['module_name', 'obj_name'])
        
        # Display settings for Pandas to ensure the table isn't truncated
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.colheader_justify', 'left')

        print("\n--- Automated Fortran Inventory ---")
        # to_string() creates a clean table without needing external libraries
        print(df.to_string(index=False))
        
        # Save to CSV for use in Excel or other tools
        output_file = "fortran_inventory.csv"
        df.to_csv(output_file, index=False)
        print(f"\nSuccessfully found {len(df)} objects. Data saved to '{output_file}'.")
    else:
        print("No Fortran routines found in the specified directory.")