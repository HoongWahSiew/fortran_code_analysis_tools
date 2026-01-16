from . import adjacency_matrix
import argparse
import pandas as pd
import sys
from . import check_object
from . import sort_matrix   

def main():
    parser = argparse.ArgumentParser(
        description="Generate Fortran routine adjacency matrix and inventory."
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default=".",
        help="Directory containing Fortran source files"
    )
    parser.add_argument(
        "--output-matrix",
        default="fortran_adjacency_matrix.csv",
        help="Output CSV file for adjacency matrix"
    )
    parser.add_argument(
        "--output-inventory",
        default="fortran_routine_inventory.csv",
        help="Output CSV file for routine inventory"
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        default=False,
        help="Do not generate routine inventory"
    )
    parser.add_argument(
        "--no-matrix",
        action="store_true",
        default=True,
        help="Do not generate adjacency matrix"
    )
    args = parser.parse_args()

    # Generate adjacency matrix
    matrix = adjacency_matrix.generate_fortran_matrix(args.dir)
    sorted_matrix = sort_matrix.reorder_by_sum(matrix)

    # Add total connectivity column, only count axis=1 (rows), that is how many routines call this routine
    connectivity = sorted_matrix.sum(axis=1)
    sorted_matrix.insert(0, 'total_connectivity', connectivity)
    print(f"Append adjacency matrix with connectivity")
    if not args.no_matrix:
        sorted_matrix.to_csv(args.output_matrix)
        print(f"Adjacency matrix saved to {args.output_matrix}")

    # Generate routine inventory
    inventory_df = check_object.scan_fortran_directory(args.dir)
    if not inventory_df.empty:
        if not args.no_inventory:
            inventory_df.to_csv(args.output_inventory, index=False)
            print(f"Routine inventory saved to {args.output_inventory}")
    else:
        print("No routines found for inventory.")
        
    # Append matrix with module and type information
    if not inventory_df.empty:
        module_info = inventory_df.set_index('obj_name')[['module_name', 'type']]
        extended_matrix = sorted_matrix.join(module_info, how='left')
        # move module_name and type to 2nd and 3rd columns
        extended_matrix = extended_matrix.reset_index()
        cols = extended_matrix.columns.tolist()
        cols.insert(1, cols.pop(cols.index('module_name')))
        cols.insert(2, cols.pop(cols.index('type')))
        extended_matrix = extended_matrix[cols]
        extended_output = "extended_" + args.output_matrix
        extended_matrix.to_csv(extended_output, index=False)
        print(f"Extended adjacency matrix with module info saved to {extended_output}")
        
    
if __name__ == "__main__":
    main()