import xlsxwriter
import data

def get_days(shift_tuples):
    """Get the list of day names, in order,
    from a shift tuple list.
    """
    daylist = []
    for s in shift_tuples:
        if s[0] not in daylist:
            daylist.append(s[0])
    return daylist

def get_people(preferences):
    return list(set([p[2] for p in preferences]))

def write_to_file(filename, shift_tuples, preferences, assignments=None):
    workbook = xlsxwriter.Workbook(filename)
    shifts_wb = workbook.add_worksheet(name="shifts")
    time_f = workbook.add_format({'num_format': 'hh:mm'})
    
    # Shifts
    
    ## Headers
    for idx, txt in enumerate(["Day", "ShiftID", "Capacity", "Begin", "End", "strID"]):
        shifts_wb.write(0, idx, txt)

    for rowidx, shift_tuple in enumerate(shift_tuples, start=1):
        shifts_wb.write(rowidx, 0, shift_tuple[0]) # Day
        shifts_wb.write(rowidx, 1, shift_tuple[1]) # ShiftId
        shifts_wb.write(rowidx, 2, shift_tuple[2]) # Capacity
        shifts_wb.write(rowidx, 3, shift_tuple[3]/(24*60), time_f) # Begin time
        shifts_wb.write(rowidx, 4, shift_tuple[4]/(24*60), time_f) # End time
        shifts_wb.write(rowidx, 5, str(shift_tuple[0])+str(shift_tuple[1])) # strID - should be unique
    
    # Preferences
    ## Generate pref[(day_id, shift_id, person_id)] = pref_score or None
    pref = dict()
    days = get_days(shift_tuples)
    people = get_people(preferences)
    for s in shift_tuples: # Default to None
        for person in people:
            pref[s[0], s[1], person] = None
    for p in preferences:
        pref[days[p[0]],p[1], p[2]] = p[3]
    
        
    pref_wb = workbook.add_worksheet(name="preferences")
    # Write to the sheet
    ## Headers
    for idx, txt in enumerate(["strID"] + people):
        pref_wb.write(0, idx, txt)

    for rowidx, s in enumerate(shift_tuples, start=1):
        pref_wb.write(rowidx, 0, str(s[0])+str(s[1])) # strID
        for colidx, p in enumerate(people, start=1):
            pref_wb.write(rowidx, colidx, pref[s[0],s[1], p])

    workbook.close()
    
if __name__ == "__main__": # For testing only
    write_to_file("beosztas.xlsx", data.shifts_from_json("psr.json"), data.preferences_from_csv("shift-optimize-PSRJanuar04-10.csv"))
