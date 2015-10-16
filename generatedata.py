import os
import os.path as pth
import sys
sys.path.append('/home/murakami/lib/python2.7/site-packages/')
                                        # remove this line!
from brian import *
from brian.hears import *
from scipy.signal import resample
from VTL_API.parWav_fun import parToWave
import numpy as np
import gzip
import argparse






##########################################################
#
# Support functions:
#  - correct_initial(sound)
#  - get_resampled(sound)
#  - get_extended(sound)
#  - drnl(sound, n_channels)
#  - get_syllables(n_syll, sensorimotor) NOT USED
#  - get_label(activations, i_syll, n_syll)
#
##########################################################


def correct_initial(sound):
  """ function for removing initial burst from sounds"""

  low = 249                             # duration of initial silence
  for i in xrange(low):                 # loop over time steps during initial period
    sound[i] = 0.0                      # silent time step

  return sound


#*********************************************************


def get_resampled(sound):		
  """ function for adapting sampling frequency to AN model
	    VTL samples with 22kHz, AN model requires 50kHz"""

  target_nsamples = int(50*kHz * sound.duration)
                                        # calculate number of samples for resampling
                                        # (AN model requires 50kHz sampling rate)
  resampled = resample(sound, target_nsamples)
                                        # resample sound to 50kHz
  sound_resampled = Sound(resampled, samplerate = 50*kHz)
                                        # declare new sound object with new sampling rate
  return sound_resampled


#*********************************************************


def get_extended(sound):		
  """ function for adding silent period to shortened vowel
	     ESN requires all samples to have the same dimensions"""

  target_nsamples = 36358               # duration of longest sample
  resized = sound.resized(target_nsamples)
                                        # resize samples
  return resized


#*********************************************************


def drnl(sound, n_channels=50):
  global uncompressed
  """ use predefined cochlear model, see Lopez-Poveda et al 2001"""
  cf = erbspace(100*Hz, 8000*Hz, n_channels)    # centre frequencies of ERB scale
                                        #  (equivalent rectangular bandwidth)
                                        #  between 100 and 8000 Hz
  drnl_filter = DRNL(sound, cf, type='human')
                                        # use DNRL model, see documentation
  print 'processing sound'
  out = drnl_filter.process()           # get array of channel activations
  if not uncompressed:
      out = out.clip(0.0)                    # -> fast oscillations can't be downsampled otherwise
      out = resample(out, int(round(sound.nsamples/1000.0)))
                                        # downsample sound for memory reasons
  return out


#*********************************************************


def get_initial_params_r(vowel):
  global infant
  """       function for getting vowels, depending on predefined number of vowels
       	     sets vocal shapes for VTL simulations
       	     also outputs teacher signal for ESN learning:
	     - simple 'labels' for classification
	     - motor parameters for regression
            NOT USED IN CURRENT VERSION"""

  lib_syll =  ['a','u','i','@','o','e','E:','2','y','A','I','E','O','U','9','Y','@6']
                                        # all available vowel shapes of the adult speaker
                                        #  'a', 'u', 'i' are also available to the infant speaker
  lib_params_ad = [                        # contains all 18 motor parameters for each vowel:
                                        #  HX, HY, JA, LP, LD, VS, TCX, TCY, TTX, TTY,
                                        #  TBX, TBY, TRX, TRY, TS1, TS2, TS3, TS4
    [0.3296, -4.2577, -4.3032, 0.0994, 0.8095, 1.0, -0.1154, -2.0006, 4.2957, -1.3323, 3.0737, -0.3857, -2.8066, -2.9354, 1.3360, -0.176, 0.638, 0.1], #a
    [1.0, -5.6308, -4.0217, 1.0, 0.2233, 0.5847, 0.6343, -0.9421, 2.7891, -0.694, 2.4431, 0.3572, -1.3615, -2.8154, 1.4, 0.212, 0.075, -0.05], #u
    [0.858, -5.2436, -1.8808, -0.091, 0.6751, 0.1438, 2.5295, -0.5805, 4.6333, -0.8665, 3.9, 0.646, -0.17, -0.7805, 1.316, 0.044, -0.165, -0.374], #i
    [0.6259, -4.8156, -4.6286, 0.1203, 0.6552, 0.5709, 1.3037, -1.9642, 4.8069, -1.019, 3.3425, -0.3516, -1.7212, -1.9642, 0.752, 0.696, 0.9, 0.256], #@
    [0.5314, -5.1526, -6.2288, 0.7435, 0.1846, 0.503, -0.1834, -1.0274, 2.4269, -1.1931, 2.0194, 0.1551, -1.3385, -2.6564, 0.556, -0.392, 0.0, 0.05], #o
    [0.44, -4.0949, -2.6336, -0.1571, 0.7513, 0.4073, 2.5611, -0.836, 4.6531, -0.954, 4.0, 0.3971, -0.2859, -0.986, 1.288, 0.364, 0.084, 0.05], #e
    [0.2855, -3.8773, -4.4288, -0.0779, 0.9028, 0.7254, 1.5777, -1.2765, 4.6663, -1.4092, 3.3823, 0.4576, -1.399, -1.4265, 1.116, 0.28, 0.28, -0.172], #E:
    [0.0, -5.3323, -4.783, 0.7696, 0.1842, 0.0, 2.0809, -0.8076, 4.5543, -1.6385, 3.246, 0.6243, -0.7338, -2.1658, 1.322, 0.678, 0.286, 0.31], #2
    [0.3687, -4.7996, -4.0264, 0.95, 0.2213, 0.0, 2.5619, -0.6172, 4.5371, -1.0007, 4.0, 0.6917, -0.8435, -1.2999, 1.376, -0.004, 0.128, -0.066], #y
    [0.0, -4.1194, -4.4544, 0.158, 0.8384, 1.0, 0.3641, -1.7675, 4.4351, -1.4577, 2.3297, -0.2184, -2.6108, -2.0473, 0.984, 0.164, 0.41, 0.102], #A
    [0.5894, -5.2554, -3.0982, -0.0144, 0.6779, 0.5438, 1.8501, -1.6542, 4.6082, -0.9248, 3.1525, 0.4213, -0.7903, -2.0108, 1.1440, 1.192, 0.844, -0.032], #I
    [0.1217, -4.4025, -4.4901, 0.0897, 0.8476, 0.7073, 1.2643, -2.2279, 4.6082, -1.2313, 2.6195, 0.1015, -1.3089, -2.4666, 0.746, 0.612, 1.04, 0.108], #E
    [0.3071, -4.9757, -5.0457, 0.4382, 0.4659, 0.8572, -0.4054, -1.7616, 4.0087, -1.7642, 2.4237, -1.4012, -2.6474, -3.1367, -0.168, 0.42, 0.252, 0.274], #O
    [0.5906, -4.6291, -4.4199, 0.5426, 0.2301, 0.83, 0.3774, -1.0846, 4.6549, -1.2545, 2.876, -0.7049, -2.6489, -1.1346, 0.028, -0.022, 0.646, -0.006], #U
    [0.0495, -5.1489, -4.7772, 0.4879, 0.4204, 0.9, 0.2443, -2.2906, 4.7649, -1.6844, 2.449, -0.7089, -2.258, -2.3853, 0.224, 0.784, 1.344, 0.56], #9
    [0.2806, -6.0, -5.0351, 0.6673, 0.3368, 0.1302, 0.4509, -1.9506, 4.8183, -1.2812, 2.7057, -0.6178, -1.6015, -3.6432, 0.874, 0.022, 0.424, 0.314], #Y
    [0.0458, -4.9823, -47772, 0.1224, 0.8423, 0.7618, 0.2609, -2.074, 4.2752, -1.6043, 2.5629, -0.9513, -2.2811, -2.667, 0.28, 0.672, 0.84, 0.416]] #@6

  lib_params_in = [
    [0.3296, -2.3640, -4.3032, 0.0994, 0.8196, 1.0, -0.4878, -1.2129, 1.9036, -1.5744, 1.3212, -1.0896, -2.4673, -1.7963, 1.0313, -0.1359, 0.4925, 0.0772], #a
    [0.9073, -3.2279, -4.0217, 1.0, 0.3882, 0.5847, 0.3150, -0.5707, 2.0209, -1.0122, 1.8202, -0.1492, -1.2155, -0.8928, 0.5620, 0.1637, 0.0602, -0.0386], #u
    [0.8580, -2.9237, -1.8808, -0.0321, 0.5695, 0.1438, 0.6562, -0.3901, 2.6431, -0.6510, 2.1213, 0.3124, -1.2385, -0.5088, 0.3674, 0.034, -0.1274, -0.2887], #i
    [1.0, -2.643, -2.0, -0.07, 0.524, 0.0, -0.426, -0.767, 2.036, -0.578, 1.163, 0.321, -1.853, -1.7267, 0.0, 0.046, 0.116, 0.116]] #@


  vowel_dic = {lib_syll[i]:i for i in range(len(lib_syll))}
  if infant:
    lib_params = lib_params_in
  else:
    lib_params = lib_params_ad

  vowel_index = vowel_dic[vowel]
  abs_params = lib_params[vowel_index]
  rel_params = get_rel_coord(abs_params)

  return rel_params


#*********************************************************


def get_label(activations, i_syll, n_syll):
    """ function for creating a teacher signal corresponding
         to given speech sound
            - activations: output of DRNL model
            - i_syll: index of current label
            - n_syll: total number of labels"""

    print 'getting label'

    len_act = len(activations)          # number of time steps

    for i in xrange(len_act):           # loop over time steps
        if (activations[i] > 0.01).any(): # check where sound signal actually starts
            low = i                     # time step index of signal start
            break                       # end loop

    for i in xrange(len_act-1, 0, -1): # loop backwards over time steps starting from the last one
        if (activations[i] > 0.01).any(): # check where sound signal actually ends
            high = i                    # time step index of signal end
            break                       # end loop


    goal = np.ones(n_syll)              # prepare teacher signal for the classification:
                                        #  label 'a' (0): [1, -1, -1,...]
                                        #  label 'u' (1): [-1, 1, -1,...] and so on
    goal = -goal                        # put -1 in place of each label
    goal[i_syll] = 1.                   # put 1 in place of current vowel


    label = -1 * np.ones([len_act, n_syll])
    for i in xrange(low, high):         # only put non-zeros where signal is actually present
        label[i] = goal                 # put goal array during signal


    return label.copy()                # return copy of label array



def get_abs_coord(x):
    global infant

    if infant:
        low_boundaries = np.array([0.0, -3.228, -7.0, -1.0, -1.102, 0.0, -3.194, -1.574, 0.873, -1.574, -3.194, -1.574, -4.259, -3.228, -1.081, -1.081, -1.081, -1.081])
        high_boundaries = np.array([1.0, -1.85, 0.0, 1.0, 2.205, 1.0, 2.327, 0.63, 3.2, 1.457, 2.327, 2.835, 1.163, 0.079, 1.081, 1.081, 1.081, 1.081])
    else:
        low_boundaries = np.array([0.0, -6.0, -7.0, -1.0, -2.0, 0.0, -3.0, -3.0, 1.5, -3.0, -3.0, -3.0, -4.0, -6.0, -1.4, -1.4, -1.4, -1.4])
        high_boundaries = np.array([1.0, -3.5, 0.0, 1.0, 4.0, 1.0, 4.0, 1.0, 5.5, 2.5, 4.0, 5.0, 2.0, 0.0, 1.4, 1.4, 1.4, 1.4])

    abs_coord = np.zeros(18)
    for i in xrange(18):
        abs_coord[i] = low_boundaries[i] + x[i] * (high_boundaries[i] - low_boundaries[i])

    return abs_coord




def get_rel_coord(x):
    global infant

    if infant:
        low_boundaries = np.array([0.0, -3.228, -7.0, -1.0, -1.102, 0.0, -3.194, -1.574, 0.873, -1.574, -3.194, -1.574, -4.259, -3.228, -1.081, -1.081, -1.081, -1.081])
        high_boundaries = np.array([1.0, -1.85, 0.0, 1.0, 2.205, 1.0, 2.327, 0.63, 3.2, 1.457, 2.327, 2.835, 1.163, 0.079, 1.081, 1.081, 1.081, 1.081])
    else:
        low_boundaries = np.array([0.0, -6.0, -7.0, -1.0, -2.0, 0.0, -3.0, -3.0, 1.5, -3.0, -3.0, -3.0, -4.0, -6.0, -1.4, -1.4, -1.4, -1.4])
        high_boundaries = np.array([1.0, -3.5, 0.0, 1.0, 4.0, 1.0, 4.0, 1.0, 5.5, 2.5, 4.0, 5.0, 2.0, 0.0, 1.4, 1.4, 1.4, 1.4])

    rel_coord = np.zeros(18)
    for i in xrange(18):
        rel_coord[i] = (x[i] - low_boundaries[i]) / (high_boundaries[i] - low_boundaries[i])

    return rel_coord







###########################################################
#
# Argument parsing
#
###########################################################


""" Arguments passed in  command line:
     vowel(str)  [--n_channels [int] / -n [int]]  [--uncompressed / -u] [--separate / -s] [--verbose / -v]"""



parser = argparse.ArgumentParser()
parser.add_argument('vowel', type=str, help='vowel to be generated')
parser.add_argument('-n', '--n_channels', nargs='?', type=int, default=50, help='number of channels to be used')
parser.add_argument('-u', '--uncompressed', action='store_true', help='use uncompressed DRNL output?')
parser.add_argument('-s', '--separate', action='store_true', help='use infant data as test samples only?')
parser.add_argument('-v', '--verbose', action='store_true', help='increase verbosity?')
parser.add_argument('-i', '--infant', action='store_true', help='simulate infant speaker?')
parser.add_argument('-S', '--sigma', nargs='?', type=float, default=0.1, help='sampling width of noise')
parser.add_argument('-N', '--n_samples', nargs='?', type=int, default=100, help='number of generated samples')
parser.add_argument('-m', '--monotone', action='store_true', help='generate monotone vowels?')

args = parser.parse_args()
vowel = args.vowel
n_channels = args.n_channels
separate_ = args.separate
uncompressed = args.uncompressed
infant = args.infant
sigma = args.sigma
n_samples = args.n_samples
monotone = args.monotone


print 'generating '+vowel+' samples, infant mode: '+str(infant)







##########################################################
#
# Main script
#
##########################################################

np.random.seed()                        # numpy random seed w.r.t. global runtime
if infant:
    speaker = 'infant'
else:
    speaker = 'adult'

initial_params_r = get_initial_params_r(vowel)

for i_global in xrange(n_samples):

    name = 'data/temp/'+vowel+'/'+vowel+'_'+str(i_global)
    filename_act = name+'.dat.gz'
    filename_wav = name+'.wav'              # declare sound file name of current simulation

    invalid = True
    while invalid:
        noise = np.random.randn(18) * sigma      # standard normally distributed vector
        x = initial_params_r + noise    # add mutation, Eq. 37
        invalid = (x < 0.0).any() or (x > 1.0).any()
        if invalid:
            print 'sample rejected. resampling.'
    params_tot = get_abs_coord(x)


    ############### Sound generation

    wavFile = parToWave(params_tot, speaker=speaker, simulation_name=vowel, different_folder=filename_wav, monotone=monotone)
                                        # call gesToWave to generate sound file
    print 'wav file '+str(wavFile)+' produced'

    sound = loadsound(wavFile)          # load sound file for brian.hears processing
    print 'sound loaded'
    sound = correct_initial(sound)      # call correct_initial to remove initial burst

    sound_resampled = get_resampled(sound)
                                        # call get_resampled to adapt generated sound to AN model
    sound_extended = get_extended(sound_resampled)
                                        # call get_extended to equalize duration of all sounds
    sound_extended.save(wavFile)        # save current sound as sound file

    print 'sound acquired, preparing sound processing'


    ############### Audio processing


    out = drnl(sound_extended, n_channels)          # call drnl to get cochlear activation
    print 'writing auditory nerve response'

    outputfile = gzip.open(filename_act, 'wb')
                                        # create and open new output file in gzip write mode
    out.dump(outputfile)
                                        # dump numpy array into output file
    outputfile.close()                  # close file



##########################################################
#
# Output
#
##########################################################


print 'done'
