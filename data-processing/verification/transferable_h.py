def all():
    group2 = [2, 3, 5, 6, 9, 10, 11, 12, 13, 15, 16, 19, 20, 21, 25]
    group3 = [3, 6, 13, 16]
    group4 = [4, 11, 14, 18, 21, 25]
    group5 = [5, 6, 9, 10, 11, 15, 16, 19, 20, 21, 25]
    group6 = [6, 16]
    group7 = [7, 8, 11, 17, 21, 25]
    group8 = [8, 11, 17, 21, 25]
    group9 = [9, 10, 19, 20]
    group10 = [10, 20]
    group11 = [11, 21, 25]
    group12 = [12, 13, 15, 16, 19, 20, 21, 25]
    group13 = [13, 16]
    group14 = [14, 18, 21, 25]
    group15 = [15, 16, 19, 20, 21, 25]
    group16 = [16]
    group17 = [17, 21, 25]
    group18 = [18]
    group19 = [19, 20]
    group20 = [20]
    group21 = [21, 25]
    group22 = [22, 23]
    group23 = [23]
    group24 = [24]
    group25 = [25]

    transferableGroups = [group2, group3, group4, group5, group6, group7, group8, group9, group10, group11, group12, group13, group14, group15, group16, group17, group18, group19, group20, group21, group22, group23, group24, group25]

    return transferableGroups

def groupby_isa():
    group2 = [2, 12, 13, 19, 23, 28]
    group3 = [3, 4, 5, 6, 9, 10, 11, 12, 14, 15, 16, 17, 20, 21, 22, 23, 28]
    group4 = [4, 6, 10, 15, 17, 21]
    group5 = [5, 6, 9, 10, 11, 12, 16, 17, 20, 21, 22, 23, 28]
    group6 = [6, 10, 17, 21]
    group7 = [7, 8, 12, 18, 23, 28]
    group8 = [8, 12, 18, 23, 28]
    group9 = [9, 10, 11, 20, 21, 22]
    group10 = [10, 21]
    group11 = [11, 22]
    group12 = [12, 23, 28]
    group13 = [13, 19, 23, 28]
    group14 = [14, 15, 16, 17, 20, 21, 22, 23, 28]
    group15 = [15, 17, 21]
    group16 = [16, 17, 20, 21, 22, 23, 28]
    group17 = [17, 21]
    group18 = [18, 23, 28]
    group19 = [19]
    group20 = [20, 21, 22]
    group21 = [21]
    group22 = [22]
    group23 = [23, 28]
    group24 = [24, 25, 27]
    group25 = [25, 27]
    group26 = [26, 27]
    group27 = [27]
    group28 = [28]

    transferableGroups = [group2, group3, group4, group5, group6, group7, group8, group9, group10, group11, group12, group13, group14, group15, 
                          group16, group17, group18, group19, group20, group21, group22, group23, group24, group25, group26, group27, group28]
    
    return transferableGroups

def mat_mul():
    group2 = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    group3 = [3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15]
    group4 = [4, 5, 8, 9, 15]
    group5 = [5, 8, 9, 15]
    group6 = [6, 7, 8, 9, 13, 14]
    group7 = [7, 9, 14]
    group8 = [8, 9]
    group9 = [9]
    group10 = [10, 11, 12, 13, 14]
    group11 = [11, 12, 13, 14]
    group12 = [12, 14]
    group13 = [13, 14]
    group14 = [14]
    group15 = [15]

    transferableGroups = [group2, group3, group4, group5, group6, group7, group8, group9, group10, group11, group12, group13, group14, group15]

    return transferableGroups

def mat_mul_for_c5a_large():
    group2 = [2, 3, 4, 5]
    group3 = [3, 4, 5]
    group4 = [4, 5]
    group5 = [5]

    transferableGroups = [group2, group3, group4, group5]

    return transferableGroups

def flag():
    group2 = [2, 3, 4, 5, 6, 7, 14, 17]
    group3 = [3, 4, 5, 6, 7, 14, 17]
    group4 = [4, 5, 14, 17]
    group5 = [5]
    group6 = [6, 7, 14, 17]
    group7 = [7, 17]
    group8 = [8, 9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23, 24]
    group9 = [9, 10, 11, 12, 13, 18, 19, 20, 21, 22, 23, 24]
    group10 = [10, 12, 13, 19, 20, 23, 24]
    group11 = [11, 13, 21, 22, 23, 24]
    group12 = [12, 13, 23, 24]
    group13 = [13, 23, 24]
    group14 = [14, 17]
    group15 = [15, 16]
    group16 = [16]
    group17 = [17]
    group18 = [18, 19, 20, 21, 22, 23, 24]
    group19 = [19, 20, 23, 24]
    group20 = [20, 24]
    group21 = [21, 22, 23, 24]
    group22 = [22, 24]
    group23 = [23, 24]
    group24 = [24]
    group25 = [25, 31]
    group26 = [26, 27, 28, 29, 30, 32, 33, 34]
    group27 = [27, 28, 30, 32, 33, 34]
    group28 = [28, 33]
    group29 = [29, 30, 34]
    group30 = [30, 34]
    group31 = [31]
    group32 = [32, 33, 34]
    group33 = [33]
    group34 = [34]
    group35 = [35]
    group36 = [36]
    group37 = [37, 38]
    group38 = [38]

    transferableGroups = [group2, group3, group4, group5, group6, group7, group8, group9, group10, group11, group12, group13, group14, group15, 
                        group16, group17, group18, group19, group20, group21, group22, group23, group24, group25, group26, group27, group28, 
                        group29, group30, group31, group32, group33, group34, group35, group36, group37, group38]
    
    return transferableGroups