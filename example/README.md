# Example Data

This directory contains example input files for testing the surface analysis tool.

## Files

- `005-avg.xyz` - Example XYZ measurement data file (63MB)
- `005-avg.txt` - Pre-processed example data (2.3MB)

## Usage

To test the tool with example data:

```bash
python3 process_xyz.py
```

Or use the Streamlit app:

```bash
streamlit run app.py
```

Then upload `005-avg.xyz` from this directory.

## Output

All analysis results will be saved to the `output/` directory.
