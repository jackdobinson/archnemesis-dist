
# CONSTANTS #

k_B                  : float    = 1.380649E-23                                   # J/K           Boltzmann constant
k_boltzmann          : float    = 1.380649E-23                                   # J/K           Boltzmann constant
k_boltzmann_cgs      : float    = 1.380649E-16                                   # erg/K         Boltzman constant (cgs)

sig_B                : float    = 5.67037E-8                                     # W m-2 K-4     Stephan Boltzmann constant

R                    : float    = 8.31446261815324                               # J mol-1 K-1   universal gas constant
R_cgs                : float    = 8.31446261815324E7                             # erg mol-1 K-1 universal gas constant (cgs)

G                    : float    = 6.67199976E-11                                 # m3 kg-1 s-2   universal gravitational constant

eps_LJ               : float    = 59.7*5.67037E-8                                # J             depth of the Lennard-Jones potential well for H2

H2_c_p               : float    = 14300.0                                        # J K-1         hydrogen specific heat

c_light              : float    = 2.99792458E8                                   # m/s           Speed of light
c_light_cgs          : float    = 2.99792458E10                                  # cm/s          Speed of light (cgs)

h_planck             : float    = 6.62607015E-34                                 # J s           Plancks constant
h_planck_cgs         : float    = 6.62607015E-27                                 # erg s         Plancks constant (cgs)
hbar_planck          : float    = 1.05457182E-34                                 # J s           Plancks constant divided by 2*PI

ref_temp             : float    = 296.0                                          # K             A reference temperature

c2                   : float    = c_light * h_planck / k_boltzmann               # m K
c2_cgs               : float    = c_light_cgs * h_planck_cgs / k_boltzmann_cgs   # cm K

N_avogadro           : float    = 6.02214129E+23                                 # mol^{-1}      Avogadro's number, number of items in one mole

igl_rho_n_STP        : float    = 2.687E+25                                      # m^{-3}        Ideal gas law number density (number of molecules per volume) at standard temperature and pressure
igl_rho_n_STP_cgs    : float    = 2.687E+19                                      # cm^{-3}       Ideal gas law number density (number of molecules per volume) at standard temperature and pressure
igl_rho_n_STP_um     : float    = 2.687E+7                                       # um^{-3}       Ideal gas law number density (number of molecules per volume) at standard temperature and pressure



# CONVERSIONS #


## Conversions - LENGTH ##

# from meters
m_to_cm              : float    = 1E2                                            # cm/m          meters to centimeters
m_to_um              : float    = 1E6                                            # um/m          meters to microns

# from centimeters
cm_to_m              : float    = 1E-2                                           # m/cm          centimeters to meters
cm_to_um             : float    = 1E4                                            # um/cm         centimeters to microns

# from microns
um_to_cm             : float    = 1E-4                                           # cm/um         microns to cm
um_to_m              : float    = 1E-6                                           # m/um          microns to m


## Conversions - AREA ##

# from meters
m2_to_cm2              : float    = 1E4                                          # cm^2/m^2      square meters to square centimeters
m2_to_um2              : float    = 1E12                                         # um^2/m^2      square meters to square microns

# from centimeters
cm2_to_m2              : float    = 1E-4                                         # m^2/cm^2      square centimeters to square meters
cm2_to_um2             : float    = 1E8                                          # um^2/cm^2     square centimeters to square microns

# from microns
um2_to_cm2             : float    = 1E-8                                         # cm^2/um^2     square microns to square cm
um2_to_m2              : float    = 1E-12                                        # m^2/um^2      square microns to square m


## Conversions - VOLUME ##

# from meters
m3_to_cm3              : float    = 1E6                                          # cm^3/m^3      cubic meters to cubic centimeters
m3_to_um3              : float    = 1E18                                         # um^3/m^3      cubic meters to cubic microns

# from centimeters
cm3_to_m3              : float    = 1E-6                                         # m^3/cm^3      cubic centimeters to cubic meters
cm3_to_um3             : float    = 1E12                                         # um^3/cm^3     cubic centimeters to cubic microns

# from microns
um3_to_cm3             : float    = 1E-12                                        # cm^3/um^3     cubic microns to cubic cm
um3_to_m3              : float    = 1E-18                                        # m^3/um^3      cubic microns to cubic m


## Conversions - PRESSURE ##

# from Pascals
pascal_to_atm           : float   = 1.0/101325.0                                 # atm/Pa        atmospheres to Pascal
pascal_to_bar           : float   = 1E-5                                         # bar/Pa        bar to Pascal

# from atmospheres
atm_to_pascal           : float    = 101325.0                                    # Pa/atm        Atmospheres to Pascals
atm_to_bar              : float    = atm_to_pascal*pascal_to_bar                 # bar/atm       atmospheres to bar

# from bars
bar_to_pascal           : float    = 1E5                                         # Pa/bar        Bar to Pascal
bar_to_atm              : float    = bar_to_pascal*pascal_to_atm                 # atm/bar       bar to atmospheres