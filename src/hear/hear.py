

# Class imports
# -------------------------------------------------------
	# Import the class(es) containing all the called functions and inherit all subfunctions
from src.hear.hear_functions import functions as funcs

	


# General imports
# -------------------------------------------------------
from datetime import date
import os
from os import system
import pickle
import gzip
import random
import mdp
import scipy as sp
import numpy

#global Oger
import Oger

import matplotlib
matplotlib.use('Agg')

#global pylab
import pylab

from pdb import set_trace as debug
	
class hear(funcs):
	
	
	
	def __init__(self):
		# Import all relevant parameters/functions as self. Since the class 'funcs' uses 
		# 'params' as a base class, we're also importing all variables in get_params as self.
		funcs.__init__(self)
	
		
	def main(self):	
		"""
		hear.main() does the auditory learning with the BRIAN hears and the echo state
		network (ESN).
		Initialize..

		Murakami:
		# n_training used to be 183
		# n_samples used to be 204
		"""
		
		# Setting up correct paths and folders
		self.setup_folders()
			
	
		# Make reservoir states inspectable for plotting..
		self.make_Oger_inspectable()
		
		
		# Only partially train the ESN.  analysis. See get_params.
		if self.generalisation_age:
			# Basically run through most of what we've done already, but for different sample data.
			# Train only on speakers that are over the age of firstspeaker_male.
			# --------------------------------------------------------------------------------------------------------------
			
			# Get the first speaker to include in data samples.
			# -------------------------------------------------------------------------
			try:
				firstspeaker_male = self.age_m.index(self.generalisation_age)
			except ValueError:
				print "Error! No generalisation age!"
				debug()
			try:
				firstspeaker_female = self.age_f.index(self.generalisation_age)
			except ValueError:
				print "Error! No generalisation age!"
				debug()
			firstspeaker = min(firstspeaker_female,firstspeaker_male)
			# -------------------------------------------------------------------------
			
			# Execute this 'setup' only by master.
			if self.rank == 0: 
				# A list of speakers that are excluded in training, but used for testing.
				self.testing_set_speakers = [speaker for speaker in self.speakers if speaker < firstspeaker]
				
		else:
			# The normal case. Train using data from all speakers. Training set and test set are randomly drawn.
			self.testing_set_speakers = False
		
		
		# Get all the samples produced in ambient speech..
		self.get_samples()
	
	
		# Simulate ESN (basically the main function, which then in itself calls the interesting function 'learn')..
		self.simulate_ESN()
					
		
		if self.rank == 0:
			self.master_collect_and_postprocess(choose=False) # SEE BELOW. Set choose True if you want to chose one of the produced ESNs for learning (essentially rename it).
		
		
		# Save this class instance
		# ---------------------------------------------------
		f = open('data/classes/hear_instance.pickle', 'w+')
		f.truncate()
		pickle.dump(self,f)
		f.close()
		
		
		
		
		
		
	
	def master_collect_and_postprocess(self,choose=True):
		"""
		# Define a neat function of all that the master does in the end.
		# This we can simply call like that, or after every time we change the samples (take away some speakers in the samples)
		# ----------------------------------------------------------------------------------------------------------------------
		Master collects all errors and confusion matrices of leaky (and non-leaky) simulations from workers
		"""
		if self.n_workers > 1:
			self.final_errors['leaky'] = comm.gather(self.errors['leaky'], root=0)
			self.final_errors['non-leaky'] = comm.gather(self.errors['non-leaky'], roo=0) if self.do_compare_leaky else []
			self.final_cmatrices['leaky'] = comm.gather(self.c_matrices['leaky'], root=0)
			self.final_cmatrices['non-leaky'] = comm.gather(self.c_matrices['non-leaky'], root=0) if self.do_compare_leaky else []
		else:
			self.final_errors['leaky'] = self.errors['leaky']
			self.final_errors['non-leaky'] = self.errors['non-leaky'] if self.do_compare_leaky else []
			self.final_cmatrices['leaky'] = self.c_matrices['leaky']
			self.final_cmatrices['non-leaky'] = self.c_matrices['non-leaky'] if self.do_compare_leaky else []
	
		# Post-processing only by master (write results to a file)
		
		
		self.write_and_plot_results()
	
	
		# Chose an output ESN for the learning.
		if choose:
			self.choose_final_ESN()

			# Analyze reward threshold (after choosing).
			if self.do_analyze_output_ESN:
				self.threshold_analysis()
		

	
