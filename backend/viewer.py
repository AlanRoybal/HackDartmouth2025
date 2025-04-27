import pydicom
import numpy as np
import os
# import re # No longer needed if only using InstanceNumber
from pathlib import Path
import napari
import argparse

# --- Configuration ---
# (No specific config needed for InstanceNumber sorting)
# --- End Configuration ---

def load_scan_using_instance_number(directory_path_str):
    """
    Loads DICOM files from a directory, sorts them based on the
    'InstanceNumber' (0020, 0013) DICOM tag, and stacks them
    into a 3D numpy array. (Identical to previous version)
    """
    dicom_path = Path(directory_path_str)
    if not dicom_path.is_dir():
        print(f"Error: Directory not found: {directory_path_str}")
        return None, None

    slices_info = []
    print(f"\n--- Scanning directory for DICOM headers: {dicom_path} ---")
    print("--- Reading 'InstanceNumber' tag for sorting ---")

    files_to_process = list(dicom_path.glob('*'))
    print(f"Found {len(files_to_process)} items. Filtering DICOMs and reading InstanceNumber...")

    processed_count = 0
    skipped_count = 0
    # First pass: Read headers and InstanceNumber
    for filepath in files_to_process:
        if filepath.is_file() and filepath.suffix.lower() in ['.dcm', '.dicom']:
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
                instance_num = ds.get("InstanceNumber")
                if instance_num is not None:
                    try:
                        slices_info.append({'path': filepath, 'InstanceNumber': int(instance_num)})
                        processed_count += 1
                    except ValueError:
                         print(f"  Warning: InstanceNumber '{instance_num}' in {filepath.name} is not a valid integer. Skipping.")
                         skipped_count += 1
                else:
                    print(f"  Warning: DICOM tag 'InstanceNumber' not found in {filepath.name}. Skipping.")
                    skipped_count += 1
            except pydicom.errors.InvalidDicomError:
                pass # Ignore non-DICOMs quietly
            except Exception as e:
                print(f"  Warning: Could not read header/tag from {filepath.name}: {e}. Skipping.")
                skipped_count += 1

    print(f"\nFinished scanning headers: Found {processed_count} files with InstanceNumber, skipped {skipped_count}.")

    if not slices_info:
        print(f"\nError: No DICOM files with a valid 'InstanceNumber' tag found in {dicom_path}.")
        return None, None

    # Sort by InstanceNumber
    print("\n--- Sorting slices by InstanceNumber ---")
    try:
        slices_info.sort(key=lambda s: s['InstanceNumber'])
    except Exception as e:
        print(f"Error during sorting by InstanceNumber: {e}")
        return None, None

    print("--- Final Sorted Order (based on InstanceNumber) ---")
    # Keep track of filenames in sorted order
    sorted_filenames = [s_info['path'].name for s_info in slices_info]
    for i, s_info in enumerate(slices_info):
        inst_num = s_info.get('InstanceNumber', 'N/A')
        print(f"  {i+1:04d}: {s_info['path'].name} (InstanceNumber: {inst_num})")
    print("--- End Sorted Order ---")


    # Second pass: Read pixel data for sorted files
    print("\n--- Reading pixel data for sorted slices ---")
    slices = []
    loaded_filenames_in_order = [] # Store filenames corresponding to loaded slices
    load_errors = 0
    pixel_data_skipped = 0

    for i, slice_info in enumerate(slices_info):
        try:
            ds = pydicom.dcmread(slice_info['path'])
            pixel_array = ds.pixel_array
            slices.append(pixel_array)
            loaded_filenames_in_order.append(slice_info['path'].name) # Keep track
        except AttributeError:
             print(f"Warning: File {slice_info['path'].name} has header but lacks pixel data (AttributeError). Skipping slice.")
             pixel_data_skipped += 1
        except Exception as e:
            print(f"Warning: Could not read pixel data for {slice_info['path'].name}: {e}. Skipping slice.")
            load_errors += 1

    if not slices:
        print("\nError: Failed to load pixel data from any DICOM files after sorting.")
        return None, None # Return None for filenames too if no volume
    if load_errors > 0 or pixel_data_skipped > 0:
         print(f"\nWarning: Encountered errors or missing pixel data for {load_errors + pixel_data_skipped} files.")

    print(f"\nSuccessfully loaded pixel data for {len(slices)} slices. Stacking into 3D volume...")

    # Stacking and shape check
    try:
        first_shape = slices[0].shape
        for idx, s in enumerate(slices):
            if s.shape != first_shape:
                print(f"\nError: Slice dimensions mismatch!")
                print(f"  Slice 0 ({loaded_filenames_in_order[0]}) shape: {first_shape}")
                print(f"  Slice {idx} ({loaded_filenames_in_order[idx]}) shape: {s.shape}")
                print("Cannot stack slices of different sizes. Volume creation failed.")
                return None, None # Return None for filenames too

        scan_volume = np.stack(slices, axis=0)
        print(f"Volume shape (slices(z), height(y), width(x)): {scan_volume.shape}")
        # Return the filenames corresponding to the successfully loaded and stacked slices
        return scan_volume, loaded_filenames_in_order
    except Exception as e:
        print(f"An unexpected error occurred during stacking: {e}")
        return None, None


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Load DICOM slices sorted by InstanceNumber and display '
                    'as a 3D volume rendering in Napari.'
    )
    parser.add_argument(
        'dicom_directory',
        type=str,
        help='Path to the directory containing the DICOM files.'
    )
    parser.add_argument(
        '--render',
        type=str,
        default='mip',
        choices=['mip', 'translucent', 'iso', 'additive'],
        help="Napari 3D rendering mode ('mip', 'translucent', 'iso', 'additive'). "
             "'translucent' often looks good but can be slower. "
             "'iso' requires setting an iso_threshold interactively in Napari."
    )
    parser.add_argument(
        '--sphere-size',
        type=float,
        default=20.0,
        help="Size of the center marker (size in pixels)."
    )
    parser.add_argument(
        '--sphere-color',
        type=str,
        default='red',
        help="Color of the center marker (e.g., 'red', 'green', 'blue', '#FF0000')."
    )

    args = parser.parse_args()
    dicom_dir = args.dicom_directory
    render_mode = args.render
    sphere_size = args.sphere_size
    sphere_color = args.sphere_color

    print(f"Attempting to load scan from: {dicom_dir}")
    print(f"Sorting by: DICOM InstanceNumber (0020, 0013)")

    scan_volume, filenames = load_scan_using_instance_number(dicom_dir)

    if scan_volume is not None:
        print(f"\nLaunching napari viewer in 3D ({render_mode} rendering)...")
        print(" - Use mouse drag to rotate the volume.")
        print(" - Use scroll wheel or right-mouse-drag to zoom.")
        print(" - Adjust contrast/brightness/colormap/rendering via controls on left.")
        if render_mode == 'iso':
            print(" - NOTE: For 'iso' rendering, you MUST adjust the 'iso_threshold' slider in the layer controls.")

        viewer = napari.Viewer()

        # Set viewer to 3D display mode *before* adding the image
        viewer.dims.ndisplay = 3
        clim = [np.min(scan_volume), np.max(scan_volume)]

        print(f"Setting initial contrast limits to: [{clim[0]:.2f}, {clim[1]:.2f}]")

        # Add the 3D volume as an image layer with specified rendering
        viewer.add_image(
            scan_volume,
            name='CT Scan 3D',
            colormap='gray', # Common starting point for CT
            contrast_limits=list(clim),
            rendering=render_mode, # Use the chosen rendering mode
            blending='additive' if render_mode == 'additive' else 'translucent' # Blending often works well with translucent/additive
            # iso_threshold=XXX # Only needed if rendering='iso', better set interactively
        )

        # Calculate the center of the volume
        z_center, y_center, x_center = np.array(scan_volume.shape) / 2
        
        # Create a points layer for the center marker
        points = np.array([[z_center, y_center, x_center]])  # Single point at center
        
        # Add the center marker as a points layer
        # Using 'disc' instead of 'sphere' (which wasn't valid)
        viewer.add_points(
            points,
            name='Center Marker',
            size=sphere_size,
            face_color=sphere_color,
            n_dimensional=True,
            opacity=0.8,
            symbol='disc'  # Changed from 'sphere' to 'disc' which is valid in napari
        )
        
        print(f"Added a {sphere_color} marker (size: {sphere_size}) at volume center: [{z_center:.1f}, {y_center:.1f}, {x_center:.1f}]")

        # Optional: Add a 3D scale bar
        # We can use the Shape layer to create a cross or axes at the center
        # Create cross-hairs at center
        if sphere_size > 0:
            # Size of cross-hairs (make relative to sphere size)
            axis_length = sphere_size * 2
            
            # Create three lines for x, y, z axes
            z_axis = np.array([[z_center-axis_length, y_center, x_center], 
                               [z_center+axis_length, y_center, x_center]])
            y_axis = np.array([[z_center, y_center-axis_length, x_center], 
                               [z_center, y_center+axis_length, x_center]])
            x_axis = np.array([[z_center, y_center, x_center-axis_length], 
                               [z_center, y_center, x_center+axis_length]])
            
            # Add each axis as a shape with different colors
            viewer.add_shapes(
                z_axis, 
                shape_type='line', 
                edge_color='blue', 
                edge_width=2,
                name='Z-Axis'
            )
            viewer.add_shapes(
                y_axis, 
                shape_type='line', 
                edge_color='green', 
                edge_width=2,
                name='Y-Axis'
            )
            viewer.add_shapes(
                x_axis, 
                shape_type='line', 
                edge_color='red', 
                edge_width=2,
                name='X-Axis'
            )
            
            print("Added coordinate axes at center (red=X, green=Y, blue=Z)")

        napari.run() # Start the napari GUI event loop

        print("Napari viewer closed.")

    else:
        print(f"\nExiting due to errors loading/processing the scan from '{dicom_dir}'. Check warnings above.")