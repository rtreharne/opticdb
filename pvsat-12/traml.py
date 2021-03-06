from tabulate import tabulate
from numpy import *
import os
from glob import glob
from csv import reader
from pylab import *
from scipy.interpolate import interp1d
from scipy.integrate import simps
import time
import db
from scipy.optimize import minimize
    

def fun(stack, TR, x, film_range, c, delta):
    for i in range(film_range[0],film_range[-1]):
        stack.d(i,x[i])
    for p in x:
        p = sqrt(x[0]**2)
    min = 1-a.average(TR, c, delta)
    return min**10

def minTR(stack, film_range, TR='R', c=0.4, delta=0.01):
    x = []
    layers = []
    bnds = []
    for i in range(film_range[0], film_range[-1]+1):
        x.append(stack.config[i][1])
        layers.append(i)
        bnds.append((5,500))

    minimize(fun, x, TR, args=(layers,c,delta), bounds=bnds, tol=1e-30, method='SLSQP')
    return 'Done'


class Stack:


    def __init__(self, filename=None, template=None, subsinf=False):
        self.subsinf = subsinf
        self.library = db.L()
        self.BASE = os.path.dirname(os.path.abspath(__file__))+'/library/'
        self.res = 200
        self.angle = 0
        self.config = []
        self.substrate(301005)
        self.exit = None
        #self.add(116604)



    def set_exit(self, material):
        return None

    def set_range(self, range):
        self.range = (range)

    def average(self, TR, c, delta, o='s'):
        x_low = self.find_nearest(self.x, c-delta)
        x_high = self.find_nearest(self.x, c+delta)
        if TR == 'T':
            T = self.get_T(option=o).real
            return mean(T[x_low:x_high])
        if TR == 'R':
            R = self.get_R(option=o).real
            return mean(R[x_low:x_high])

    def find_nearest(self, array, value):
        idx = (abs(array-value)).argmin()
        return idx
	
    def jsc(self, E=1.41):
    
        unzipped = array(zip(*self.open_file('spectrum.csv')))
        x = array(unzipped[0])/1000
        irradiance = array(unzipped[1])*1000
        irradiance_interp = interp(self.x, x, irradiance)
        flux = irradiance_interp*((self.x*1e-6)/(6.63e-34*3e8))

        lim = (6.63e-34*3e8)/(1.602e-19*E*1e-6)
        index = min(range(len(self.x)), key = lambda i: abs(self.x[i]-lim))
        T = self.get_T(option='a')# - self.get_T()
        T = (T*flux).real
        
        area = simps(T[:index], self.x[:index]) 
        jsc = 1.602e-19*area/10
        print '%s (ma/cm^2)' % jsc
        return jsc

    def plot(self, o='s'):

        fig = figure(figsize=(8,6))
        ax = fig.add_subplot(111)
	
        y1 = self.get_T(option = o).real
        y2 = self.get_R(option = o).real
        
        ax.plot(self.x, y1)
        ax.plot(self.x, y2)
        ax.set_xlim(self.range)
        ax.set_ylabel(r"$T, R$")
        ax.set_xlabel(r"Wavelength, $\lambda$ ($\mu$m)")
	
        show()

    def crunch(self, l):
        subs = self.M[0]
        mult_this = self.M[1:l+1]
        MM = self.matrix_mult(mult_this)
        B = subs[0]*MM[0][0] + subs[1]*MM[0][1]
        C = subs[0]*MM[1][0] + subs[1]*MM[1][1]
        return B, C

    def get_T(self, option='s', subs='semi'):
        l = len(self.M)
        adm = 2.6544e-3 

        #if self.exit:
        #    print 'exit medium is set'
        #else:
        exit = adm
        
        if option == 'a':
            for i in range(len(self.config)):
                if any("absorber" in  self.config[i]):
                    l = i-1
                    exit = self.N[i]*adm

        B, C = self.crunch(l)
        D = (exit*B + C)
        T = (4*exit*adm*self.N[0].real)/(D*D.conjugate())

        Ta = ((4*self.N[0].real))/((self.N[0].real)+1)**2

        if self.subsinf:
            return T
        else:
            return T*Ta

    def get_R(self, option='s'):
        l = len(self.M)
        adm = 2.6544e-3 
	exit = adm

	if option == 'a':
            for i in range(len(self.config)):
	        if any("absorber" in  self.config[i]):
	            l = i-1
	            exit = self.N[i]*adm

        B, C = self.crunch(l)
        D = (exit*B + C)
        E = (exit*B - C)
        R = (E/D)*(E/D).conjugate()

        Ra1 = ((1-self.N[0])/(1+self.N[0]))
        Ra2 = Ra1.conjugate()
        Ra = Ra1*Ra2

        Rb = (R+Ra-(2*R*Ra))/(1-(R*Ra))

        if self.subsinf:
            return R
        else:
            return Rb

    def matrix_mult(self, M):
        MM = self.identity()

        if len(M) > 0:
            for i in range(len(M)):
                MM1 = MM[0][0]
                MM2 = MM[0][1]
                MM3 = MM[1][0]
                MM4 = MM[1][1]
                
                M1 = M[i][0][0]
                M2 = M[i][0][1]
                M3 = M[i][1][0]
                M4 = M[i][1][1]

                holder1 = MM1*M1 + MM2*M3
                holder2 = MM1*M2 + MM2*M4
                holder3 = MM3*M1 + MM4*M3
                holder4 = MM3*M2 + MM4*M4

                MM = array([[holder1, holder2],[holder3, holder4]])

        return MM

    def identity(self):
        N = self.res
        I1 = array([1]*N)
        I2 = array([0]*N)
        I = array([[I1, I2],[I2,I1]])
        return I

    def matrix_element(self, N, item):
	d = item[1]
	Y = array(N)*2.6544e-3

	if item[2] =='substrate':
	    c = array([1]*len(N))
	    M = (c, Y)
	    return M
	    
	    M = array([[1]*len(N)],[Y])
	    return M
	    
        if item[2] != 'substrate':
            delta = self.delta(N, item)
            
            M1 = cos(delta)
            M2 = 1j*sin(delta)/Y 
            M3 = 1j*sin(delta)*Y
            M4 = cos(delta)

            M = array([[M1, M2], [M3, M4]])

	    return M
	

    def delta(self, N, item):
        if item[2] != 'substrate':
            delta = (N/self.x)*(2*pi*item[1]*cos(self.angle))/1000
            return delta

    def add_graded(self, mat1='ITO', mat2='CdS', loc=None, d=20, n=10):
        key = '{0}:{1}'.format(mat1, mat2)
        self.grade[key] = [mat1, mat2]
        self.add(key, d, 'graded', loc)

    def dummy(self, dummy=None):
        if dummy == None:
            self.g0 = Stack()
            return "aOK"
        else:
            return dummy
        
    def copy_film(self):
        return "something"

    def d(self, film, d):
        if film != 0:
            self.config[film][1] = d 
            self.M[film] = self.matrix_element(self.N[film], self.config[film])
            
    def graded_build(self, N, parent, l=1000, d=None):
        name = self.config[parent][0]
        graded_obj = Stack(template='empty')
        graded_obj.N = []
	graded_obj.M = []
        for i in range(l+1):
            comp = (float(i)/l)
           
            graded_obj.config.append(['{0}_{1}'.format(name, comp), float(d)/l, 'passive'])
            graded_obj.N.append(self.N[parent][0]*(1-comp)+self.N[parent][1]*(comp))
	    graded_obj.M.append(self.matrix_element(graded_obj.N[i], graded_obj.config[i]))

        self.graded_dict[name] = graded_obj 

    def build(self, res=None, repeat=False):
        tbuild = time.clock()
        
        if res:
            self.res=res

        self.N = []
        self.M = []

        min_list = []
        max_list = []

        stack_data = []

        for film in self.config:
            data = self.library.data(film[0])
            stack_data.append(data)

            min_list.append(data[0][0])
            max_list.append(data[0][-1])

        self.x = linspace(max(min_list), min(max_list), self.res)
        self.data = stack_data

        for film in stack_data:
            ninterp = interp(self.x, film[0], film[1])
            if len(film)>2:
                kinterp = interp(self.x, film[0], film[2])
            else:
                kinterp = linspace(0, 0, self.res)
            self.N.append(ninterp - kinterp*1j)
            
        i = 0
        for film in self.config:
            self.M.append(self.matrix_element(self.N[i], film))
            i += 1

        self.set_range((min(self.x), max(self.x)))


        '''
                    unzipped = list(zip(*self.film_data(i)))
                    x = unzipped[0]
                    n = unzipped[1]
                    k = unzipped[2]

                    ninterp = interp(self.x, x, n)
                    kinterp = interp(self.x, x, k)

		    N = ninterp - kinterp*1j
                    self.N.append(N)
        # WARNING: This will get expensive for lots of films

        # find the film_data with widest subset wavelength range
        # common to all film_data
        self.N = []
        self.M = []

        if res  != None:
            self.res = res
        
        if len(self.config)<2:
            # interpolate wrt res
            return "something"
        else:
            min_list = []
            max_list = []

            for i in range(len(self.config)):
                if self.config[i][2] == 'graded':
                    for j in range(len(self.grade[self.config[i][0]])):
                        filename = self.library_dict[
                                self.grade[self.config[i][0]][j]]
                        min_list.append(self.film_data(filename=filename)[0][0])
                        max_list.append(self.film_data(filename=filename)[-1][0])
                else:
                    min_list.append(self.film_data(i)[0][0])
                    max_list.append(self.film_data(i)[-1][0])
            self.x = linspace(max(min_list), min(max_list), self.res)

            for i in range(len(self.config)):
                if self.config[i][2] == 'graded':
                    N = []
                    for j in range(len(self.grade[self.config[i][0]])):
                        filename = self.library_dict[
                                self.grade[self.config[i][0]][j]]
                        unzipped = list(zip(*self.film_data(filename=filename)))
                        x = unzipped[0]
                        n = unzipped[1]
                        k = unzipped[2]
                        ninterp = interp(self.x, x, n)
                        kinterp = interp(self.x, x, k)
                        N.append(ninterp - kinterp*1j)
                    self.N.append(N)

                    self.graded_build(N, i, d = self.config[i][1])
		    self.graded_M = self.graded_dict[self.config[i][0]].M
                    self.M.append(self.matrix_mult(self.graded_M))
                    

		    #Multiply matrices together and add to self.M
                else:

                    unzipped = list(zip(*self.film_data(i)))
                    x = unzipped[0]
                    n = unzipped[1]
                    k = unzipped[2]

                    ninterp = interp(self.x, x, n)
                    kinterp = interp(self.x, x, k)

		    N = ninterp - kinterp*1j
                    self.N.append(N)
		    self.M.append(self.matrix_element(N, self.config[i]))
    '''

    def get_real(self, complex_list):
        real_list = []
        for i in range(len(complex_list)):
            real_list.append(complex_list[i].real)

        return real_list

    def get_imag(self, complex_list):
        imag_list = []
        for i in range(len(complex_list)):
            imag_list.append(-complex_list[i].imag)

        return imag_list

    def plot_N(self, film, interp='on', twin='on'):
        data = self.film_data(film)
        x = list(zip(*data)[0]) 
        y = []
        ax = gca()
        for i in range(1, len(data[0])):
            y.append(list(zip(*data)[i]))

        if twin=='on':
            ax2 = twinx(ax)
            ax.plot(x, y[0])
            ax2.plot(x, y[1])
            if interp == 'on':
                ax.plot(self.x, self.get_real(self.N[film]), 'o')
                ax2.plot(self.x, self.get_imag(self.N[film]), 'o')
        else:
            for i in range(len(y)):
                ax.plot(x, y[i])
                if interp == 'on':
                    ax.plot(self.x, self.get_real(self.N[film]), 'o')
                    ax.plot(self.x, self.get_imag(self.N[film]), 'o')
	show()
    

    def open_file(self, filename):
        with open(filename, 'rU') as f:
	    csvdata = reader(f)
	    next(csvdata) # Skip first row
	    rows = list(csvdata)
	    float_rows = [[float(i) for i in row] for row in rows] # Convert all data to float
	return float_rows
	    
    def film_data(self, film_id=None, filename=None):
        if filename == None:
            filename = self.library_dict[self.config[film_id][0]]
        return self.open_file(filename)

    def create_library(self):
        file_list = sort(os.listdir(self.BASE))
        dict_list = []
        for i in range(len(file_list)):
            dict_list.append([file_list[i].replace('.csv', ''), self.BASE+file_list[i]])
        self.library_dict = dict(dict_list)
 
    def library(self):
        for key, value in self.library_dict.iteritems():
            print key

    def substrate(self, name, d='--', film_type='substrate'):
        self.config.append([name, d,  film_type])
        #self.table()

    def add(self, name, d=100, film_type='passive', loc=None, bnds=(0, 10000), build=True):
        if loc==None:
	    self.config.append([name, d, film_type, bnds])
	else:
	    if loc>0:
	        self.config.insert(loc, [name, d, film_type, bnds])

        if build:
            self.build()
            #self.table()

    def remove(self, loc=None):
        if loc==None: # and len(self.config)>1:
	   self.config.pop()
	elif len(self.config)>1:
	   del self.config[loc]
	
        self.build()

    def table(self, film=None):
        table = []
        if film != None and self.config[film][2] == 'graded':
            self.graded_dict[self.config[film][0]].table()
        else:
            for i in range(len(self.config)):
                table.append(self.config[i][:])
                table[i].insert(0, i)

            print tabulate(table,
	                   headers=['#', 'Material', 'Thickness (nm)', 'Type'], 
	        	   tablefmt='orgtbl')

    def repeat(self, films, N):
        films = films.split(',')
        init_length = len(self.config)
        for _ in range(N):
            for film in films:
                film = int(film)
                if film < init_length:
                    if any("substrate" in  self.config[film]):
                        continue
                    else:
                        self.add(self.config[film][0], self.config[film][1], build=False)
                else:
                    pass 
        self.build()
        #self.table()

        def search(self,key):
            return self.library.search(key)




class Plot:

    def __init__(self, stack=None):
        if stack != None:
            for i in range(len(stack)):
                plot(stack[i].x, stack[i].get_T())
            show()
