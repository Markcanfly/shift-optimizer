import xlsxwriter
import data
from colour import Color

def get_days(shift_tuples):
    """Get the list of day names, in order,
    from a shift tuple list.
    """
    daylist = []
    for s in shift_tuples:
        if s[0] not in daylist:
            daylist.append(s[0])
    return daylist

def get_prefcolor(n, max_n):
    """Takes a pref score, and a worst pref score,
    and returns a color to format how good that pref score is.
    Args:
        n: the pref score
        max_n: the worst pref score for that shift
    Returns:
        color: long hex color
    """
    assert n <= max_n
    good = Color('#bef7c5')
    bad = Color('#ffd9d9')
    return list(good.range_to(bad, max_n + 1))[n].hex_l

def get_people(preferences):
    return list(set([p[2] for p in preferences]))

def write_to_file(filename, shift_tuples, pref_tuples, assignments):
    workbook = xlsxwriter.Workbook(filename)
    shifts_ws = workbook.add_worksheet(name="shifts")
    time_f = workbook.add_format({'num_format': 'hh:mm'})
    
    # Shifts
    
    ## Headers
    for idx, txt in enumerate(["Day", "ShiftID", "Capacity", "Begin", "End", "strID"]):
        shifts_ws.write(0, idx, txt)

    for rowidx, shift_tuple in enumerate(shift_tuples, start=1):
        shifts_ws.write(rowidx, 0, shift_tuple[0]) # Day
        shifts_ws.write(rowidx, 1, shift_tuple[1]) # ShiftId
        shifts_ws.write(rowidx, 2, shift_tuple[2]) # Capacity
        shifts_ws.write(rowidx, 3, shift_tuple[3]/(24*60), time_f) # Begin time
        shifts_ws.write(rowidx, 4, shift_tuple[4]/(24*60), time_f) # End time
        shifts_ws.write(rowidx, 5, str(shift_tuple[0])+str(shift_tuple[1])) # strID - should be unique
    
    # Preferences
    ## Generate pref[(day_id, shift_id, person_id)] = pref_score or None
    pref = dict()
    days = get_days(shift_tuples)
    people = get_people(pref_tuples)
    for (d,s,c,b,e) in shift_tuples: # Default to None
        del c,b,e # We don't need them here
        for person in people:
            pref[d, s, person] = None
    for (d,s,p,prefscore) in pref_tuples:
        pref[days[d],s, p] = prefscore
    
    # Write to the sheet
    pref_ws = workbook.add_worksheet(name="preferences")
    ## Headers
    for idx, txt in enumerate(["strID"] + people):
        pref_ws.write(0, idx, txt)

    for rowidx, (d,s,c,b,e) in enumerate(shift_tuples, start=1):
        del c,b,e # We don't need them here
        pref_ws.write(rowidx, 0, str(d)+str(s)) # strID
        for colidx, p in enumerate(people, start=1):
            pref_ws.write(rowidx, colidx, pref[d,s,p])
    
    # Assignments

    # Formats
    no_pref = workbook.add_format({'font_color':'#dedede'})

    assign_ws = workbook.add_worksheet(name="assignments")
    # Write to the sheet
    ## Headers
    for idx, txt in enumerate(["strID"] + people):
        assign_ws.write(0, idx, txt)

    for rowidx, (d,s,c,b,e) in enumerate(shift_tuples, start=1):
        del c,b,e # We don't need them here
        assign_ws.write(rowidx, 0, str(d)+str(s)) # strID
        for colidx, p in enumerate(people, start=1):
            if pref[d,s,p] is None:
                assign_ws.write_boolean(rowidx, colidx, assignments[d,s,p], no_pref)
            else:
                pref_color = get_prefcolor(pref[d,s,p], max([pref[d,s,p] for p in people if pref[d,s,p] is not None]))
                pref_format = workbook.add_format({'bg_color':pref_color})
                assign_ws.write_boolean(rowidx, colidx, assignments[d,s,p], pref_format)
    workbook.close()
    
if __name__ == "__main__": # For testing only
    write_to_file("beosztas.xlsx", data.shifts_from_json("psr.json"), data.preferences_from_csv("shift-optimize-PSRJanuar04-10.csv"))
