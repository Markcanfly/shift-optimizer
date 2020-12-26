import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell as celln
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

def write_to_file(filename, shift_tuples, pref_tuples, assignments, personal_reqs):
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
    
    # Personal requirements
    pers_ws = workbook.add_worksheet(name="personal_reqs")
    ## Headers
    for idx, txt in enumerate(["person","Min. hours", "Max. hours","Min. long shits","Only long shifts"]):
        pers_ws.write(0, idx, txt)
    for rowidx, p in enumerate(people, start=1):
        pers_ws.write(rowidx, 0, p)
        pers_ws.write_number(rowidx, 1, personal_reqs[p]['min'])
        pers_ws.write_number(rowidx, 2, personal_reqs[p]['max'])
        pers_ws.write_number(rowidx, 3, personal_reqs[p]['min_long_shifts'])
        pers_ws.write_boolean(rowidx, 4, personal_reqs[p]['only_long_shifts'])

    # Assignments

    # Formats
    no_pref = workbook.add_format({'font_color':'#dedede'})

    assign_ws = workbook.add_worksheet(name="assignments")
    # Write to the sheet
    ## Headers
    for idx, txt in enumerate(["strID"] + people + ["n assigned", "capacity"]):
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
    
    # Add shift capacity condition indicator
    ## Add a formula to the end of each row,
    ## to calculate the number of people assigned.
    ## Add conditional formatting to this cell,
    ## so that it's:
    ##      green,  when the shift is full
    shift_full =      workbook.add_format({'bg_color':'#a6ff9e'})
    ##      orange, when the shift is below capacity
    shift_below_cap = workbook.add_format({'bg_color': '#ffc670'})
    ##      red,    when the shift is over capacity
    shift_over_cap =  workbook.add_format({'bg_color': '#ff7a70'})
    for rowidx, (d,s,c,b,e) in enumerate(shift_tuples, start=1):
        del c,b,e # We don't need them here, because c has to be dynamic
        # Current shift state
        cap_format = workbook.add_format({'left':1})
        assign_ws.write_formula(
            rowidx, len(people)+1, 
            f'=COUNTIF({celln(rowidx, 1)}:{celln(rowidx,len(people))}, TRUE)',
            cap_format)
        # Capacity
        assign_ws.write_formula(
            rowidx, len(people)+2,
            f'=shifts!C{rowidx+1}')

        #region Conditional formatting the n_people on shift
        capacity_col_row = celln(rowidx, len(people)+2)
        # Full
        assign_ws.conditional_format(celln(rowidx, len(people)+1),
        {
            'type':'cell',
            'criteria':'==',
            'value': capacity_col_row,
            'format': shift_full
        })
        # Below capacity
        assign_ws.conditional_format(celln(rowidx, len(people)+1),
        {
            'type':'cell',
            'criteria':'<',
            'value': capacity_col_row,
            'format': shift_below_cap
        })
        # Full
        assign_ws.conditional_format(celln(rowidx, len(people)+1),
        {
            'type':'cell',
            'criteria':'>',
            'value': capacity_col_row,
            'format': shift_over_cap
        })
        #endregion  

    # Add personal requirement indicator
    ## For each person, under their last shift, indicate their:
    ## Minimum hours (from the personal_reqs sheet)
    ## The actual number of hours they are taking
    ## Maximum hours (from the personal_reqs sheet)
    ## Number of long shifts taken
    ## Minimum number of long shifts (from the personal_reqs sheet)
    ## Whether they only take long shifts (from the personal_reqs sheet)

    # Horrifying excel formula #1
    def preq_formula(person_col, var_col):
            return (f'=INDEX(personal_reqs!{celln(1,0, row_abs=True, col_abs=True)}:{celln(len(people),4, row_abs=True, col_abs=True)},'+
            f'MATCH({celln(0,person_col, row_abs=True)},personal_reqs!{celln(1,0, row_abs=True, col_abs=True)}:{celln(len(people), 0, row_abs=True, col_abs=True)},0)'
            +f',{var_col})')

    # TODO minor formatting here

    # Row headers
    for row_idx, txt in enumerate(["Min. hours", 
                         "Actual hours", 
                         "Max. hours", 
                         "Long shifts taken", 
                         "Min. long shifts", 
                         "Long shifts only"
                            ]):
        r0 = len(shift_tuples)+1
        assign_ws.write(r0+row_idx, 0, txt)

    for col_idx, p in enumerate(people, start=1):
        r0 = len(shift_tuples)+1 # Start after the last shift
        min_hours_formula = preq_formula(col_idx, 2)
        assign_ws.write_formula(r0, col_idx, min_hours_formula)
        # TODO formula to calculate actual number of hours
        max_hours_formula = preq_formula(col_idx, 3)
        assign_ws.write_formula(r0+2, col_idx, max_hours_formula)
        # TODO formula to calculate number of long shifts
        min_long_shifts_formula = preq_formula(col_idx, 4)
        assign_ws.write_formula(r0+4, col_idx, min_long_shifts_formula)
        long_shifts_only_formula = preq_formula(col_idx, 5)
        assign_ws.write_formula(r0+5, col_idx, long_shifts_only_formula)


    # Add conditional to highlight actual applications
    applied_shift_format = workbook.add_format({
        'bold': True,
        'border': 1
    })
    assign_ws.conditional_format(0,0, len(shift_tuples)+1, len(people)+1,
        {
            'type': 'cell',
            'criteria': '==',
            'value': True,
            'format': applied_shift_format
        }
    )

    workbook.close()
    
if __name__ == "__main__": # For testing only
    write_to_file("beosztas.xlsx", data.shifts_from_json("psr.json"), data.preferences_from_csv("shift-optimize-PSRJanuar04-10.csv"))
