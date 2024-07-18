# Made by Ryan P from Trace Inc. on 6/26/24 copyright
# This script utilizes pygsheets to update a Google Sheet with test results.
# https://docs.google.com/spreadsheets/d/11EKJkvS7Tr6eny0JO9gNNK8j_OL8GIRDECR4MW02P2E/edit?usp=sharing

import pygsheets

# Path to your service account JSON key file
json_keyfile = r"C:\Users\Natasha_\Desktop\keys\discharge-analysis-results-2ecd547a74ea.json"
# Google Sheet ID
spreadsheet_id = '11EKJkvS7Tr6eny0JO9gNNK8j_OL8GIRDECR4MW02P2E'
# Sheet title to update
sheet_title = 'Camera Discharge Test Results'

# Function to add data to the Google Sheet
def add_to_google_sheet(cam_ids, formatted_results):
    try:
        # Authorize pygsheets
        gc = pygsheets.authorize(service_file=json_keyfile)

        # Open the Google Sheet
        sh = gc.open_by_key(spreadsheet_id)

        # Select the first sheet (or use the title as well)
        wks = sh.worksheet_by_title(sheet_title)

        # Find the first empty row
        empty_row = len(wks.get_col(1, include_tailing_empty=False)) + 1

        # Update the Google Sheet with camera IDs and test results
        wks.update_values(f'A{empty_row}', [[cam_id, result] for cam_id, result in zip(cam_ids, formatted_results)])

        # Print success message with the link to the Google Sheet
        print("Data successfully uploaded to Google Sheets.")
        print(f"Link to the Google Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?usp=sharing")

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")

# Example usage if needed
if __name__ == "__main__":
    cam_ids = ['Camera1', 'Camera2']
    formatted_results = [
        "Camera ID: Camera1\nTotal Runtime (hours): 5.25 hours\nMinutes recorded: 315.00 minutes\nSlope: 1.50 milliV/minute\nDate: 06/26/2024 14:30:00"
    ]
    
    add_to_google_sheet(cam_ids, formatted_results)
