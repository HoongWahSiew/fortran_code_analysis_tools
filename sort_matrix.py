import pandas as pd
import argparse

def reorder_by_sum(input_file):
    # 1. Load the matrix (index_col=0 ensures names are treated as labels)
    if type(input_file) == str:
        df = pd.read_csv(input_file, index_col=0)
    else:
        df = input_file

    # 2. Reorder Rows
    # Calculate 1D array of row sums
    row_sums = df.sum(axis=1)
    # Sort names from largest sum to smallest sum
    new_row_order = row_sums.sort_values(ascending=False).index
    # Apply to the dataframe
    df = df.loc[new_row_order]

    # 3. Reorder Columns
    # Calculate 1D array of column sums
    col_sums = df.sum(axis=0)
    # Sort names from largest sum to smallest sum
    new_col_order = col_sums.sort_values(ascending=False).index
    # Apply to the dataframe
    df = df[new_col_order]

    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to the dependency CSV")
    parser.add_argument("--output", help="Output file name for reordered matrix", default="reordered_matrix.csv")
    parser.add_argument("--no-output", action="store_true", help="Do not save the output to a file")
    args = parser.parse_args()

    try:
        ordered_df = reorder_by_sum(args.file)
        
        print("\n--- Matrix Reordered by Sum (Highest Connectivity First) ---")
        print(ordered_df)
        
        if not args.no_output:
            output_name = args.output
            ordered_df.to_csv(output_name)
            print(f"\nSaved as '{output_name}'")
        
    except Exception as e:
        print(f"Error: {e}")