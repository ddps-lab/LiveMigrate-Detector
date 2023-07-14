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

def mat_mul():
    group2 = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    group3 = [3, 4, 5, 6, 7, 10, 11, 12]
    group4 = [4, 5]
    group5 = [5]
    group6 = [6, 7, 10, 11]
    group7 = [7, 11]
    group8 = [8, 9, 10, 11]
    group9 = [9, 11]
    group10 = [10, 11]
    group11 = [11]
    group12 = [12]

    transferableGroups = [group2, group3, group4, group5, group6, group7, group8, group9, group10, group11]

    return transferableGroups

def mat_mul_for_t3_large():
    group2 = [2, 3, 4, 5]
    group3 = [3, 4, 5]
    group4 = [4, 5]
    group5 = [5]

    transferableGroups = [group2, group3, group4, group5]

    return transferableGroups

def mat_mul_for_c5a_large():
    group2 = [2, 3]
    group3 = [3]

    transferableGroups = [group2, group3]

    return transferableGroups