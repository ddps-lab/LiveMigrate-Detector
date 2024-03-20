def f1():
    print('f1')
def f2():
    print('f2')
def f3():
    print('f3')
def f4():
    print('f4')
def f5():
    print('f5')
def f6():
    print('f6')
def f7():
    print('f7')    
def f8():
    print('f8')    
def f9():
    print('f9')        
def f10():
    print('f10')    
def f11():
    print('f11')
def f12():
    print('f12')
def f13():
    print('f13')
def f14():
    print('f14')
def f15():
    print('f15')
def f16():
    print('f16')

def test1():
    print('test1')
def test2():
    print('test1')
def test3():
    print('test1')
def test4():
    print('test4')
def test5():
    print('test5')
def test6():
    print('test6')
def test7():
    print('test7')
def test8():
    print('test8')
def test9():
    print('test9')
def test10():
    print('test10')
def test11():
    print('test11')
def test12():
    print('test12')
def test13():
    print('test13')
def test14():
    print('test14')
def test15():
    print('test15')

a = 10
b = 20

if a > 10:  # push cap1
    test1()
    if a < b:   # push cap2
        test2()
        if a < b:   # push cap3
            test3()
        else: # rollback cap3, pop cap3
            if a == b: # push cap3
                test4()
            else: # rollback cap3, pop cap3
                test5()   

            if a != b: # push cap3
                test6()
            else: # rollback cap3, pop3
                test7()

        test8()
    else:   # rollback cap2, pop cap2
        test6()
        if a < b:   # push cap2
            test9()
        else:   # rollback cap2, pop2
            test10()
elif a < 10:    # rollback cap1, pop cap1, push cap1
    test11()
elif a == 12:   # rollback cap1, pop cap1, push cap1
    test11()
    if a < b:   # push cap2
        test13()
    else:   # rollback cap2, pop cap2
        test14()
else:   # rollback cap1, pop cap1
    test15()

if a == 9:  # push cap1
    if a == 100:    # push cap2
        f1()
        if a == 1000:   # push cap3
            f2()
        else:   # rollback cap3, pop cap3
            f3()        
    else:   # rollback cap2, pop cap2
        f4()
    a = 10

if a == 9:  # push cap1
    if a == 100:    # push cap2
        f5()
        if a == 1000:   # push cap3
            f6()
        else:   # rollback cap3, pop cap3
            f7()        
    else:   # rollback cap2, pop cap2
        f8()
    a = 10
elif a: # rollback cap1, pop cap1, push cap1
    f9()

if a >= 10: # push cap1
    f10()
else:   # rollback cap1, pop cap1
    f11()
    if a == 100:    # push cap1
        f12()
        if a == 100:    # push cap2
            f13()
        else:   # rollback cap2, pop cap2
            f14()
    else:   # rollback cap1, pop cap1
        f15()

for _ in range(5):
    f16()