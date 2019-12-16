"""
This file contain a subclass of the model.py module and Cluster class. It
is dedicated to the computing of observables.

"""

#==================================================
# Requested imports
#==================================================

import numpy as np
import scipy.ndimage as ndimage
import astropy.units as u
from astropy.wcs import WCS
from astropy import constants as const
import scipy.interpolate as interpolate

from ClusterModel              import model_tools
from ClusterModel.ClusterTools import cluster_global 
from ClusterModel.ClusterTools import cluster_profile 
from ClusterModel.ClusterTools import cluster_spectra 
from ClusterModel.ClusterTools import cluster_xspec
from ClusterModel.ClusterTools import map_tools


#==================================================
# Observable class
#==================================================

class Observables(object):
    """ Observable class
    This class serves as a parser to the main Cluster class, to 
    include the subclass Observable in this other file.

    Attributes
    ----------  
    The attributes are the same as the Cluster class, see model.py

    Methods
    ----------  
    - get_gamma_spectrum(self, energy=np.logspace(-2,6,1000)*u.GeV, Rmax=None,type_integral='spherical', 
    NR500_los=5.0, Npt_los=100): compute the gamma ray spectrum integrating over the volume up to Rmax
    - get_gamma_profile(self, radius=np.logspace(0,4,1000)*u.kpc, Emin=10.0*u.MeV, Emax=1.0*u.PeV, 
    Energy_density=False, NR500_los=5.0, Npt_los=100): compute the gamma ray profile, integrating over 
    the energy between the gamma ray energy Emin and Emax.
    - get_gamma_flux(self, Rmax=None, type_integral='spherical', NR500_los=5.0, Npt_los=100,
    Emin=10.0*u.MeV, Emax=1.0*u.PeV, Energy_density=False): compute the gamma ray flux between 
    energy range and for R>Rmax.
    - get_gamma_template_map(self, NR500_los=5.0, Npt_los=100): compute the gamma ray template map, 
    normalized so that the integral over the overall cluster is 1.
    
    - get_ysph_profile(self, radius=np.logspace(0,4,1000)*u.kpc): compute the spherically 
    integrated compton parameter profile
    - get_ycyl_profile(self, radius=np.logspace(0,4,1000)*u.kpc): compute the cylindrincally 
    integrated Compton parameter profile
    - get_y_compton_profile(self, radius=np.logspace(0,4,1000)*u.kpc, NR500_los=5.0, Npt_los=100):
    compute the Compton parameter profile
    - get_ymap(self, FWHM=None, NR500_los=5.0, Npt_los=100): compute a Compton parameter map.

    - get_sx_profile(self, radius=np.logspace(0,4,1000)*u.kpc, NR500_los=5.0, Npt_los=100,
    output_type='S'): compute the Xray surface brightness profile
    - get_fxsph_profile(self, radius=np.logspace(0,4,1000)*u.kpc, output_type='S'): compute the Xray 
    spherically integrated flux profile
    - get_fxcyl_profile(self, radius=np.logspace(0,4,1000)*u.kpc, NR500_los=5.0, Npt_los=100,
    output_type='S'): compute the Xray cylindrically integrated flux profile
    - get_sxmap(self, FWHM=None, NR500_los=5.0, Npt_los=100, output_type='S'): compute the Xray 
    surface brigthness map

    """
    
    #==================================================
    # Compute gamma ray spectrum
    #==================================================

    def get_gamma_spectrum(self, energy=np.logspace(-2,6,100)*u.GeV,
                           Rmin=None, Rmax=None,
                           type_integral='spherical',
                           Rmin_los=None, NR500_los=5.0,
                           Cframe=False):
        """
        Compute the gamma ray emission enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the gamma ray emmission enclosed within an circular area (i.e.
        cylindrical).
        
        Parameters
        ----------
        - energy (quantity) : the physical energy of gamma rays
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - energy (quantity) : the physical energy of gamma rays
        - dN_dEdSdt (np.ndarray) : the spectrum in units of GeV-1 cm-2 s-1

        """
                
        # In case the input is not an array
        energy = model_tools.check_qarray(energy, unit='GeV')

        # K-correction
        if Cframe:
            energy_rf = energy*1.0
        else:
            energy_rf = energy*(1+self._redshift)
        
        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin
            
        # Compute the integral
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_gamma(energy_rf, rad)
            dN_dEdt = model_tools.spherical_integration(dN_dEdVdt, rad)
            
        # Compute the integral        
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_gamma(energy_rf, r3d)
            dN_dEdt = model_tools.cylindrical_integration(dN_dEdVdt, energy, r3d, r2d, los, Rtrunc=self._R_truncation)
        
        # From intrinsic luminosity to flux
        dN_dEdSdt = dN_dEdt / (4*np.pi * self._D_lum**2)

        # Apply EBL absorbtion
        if self._EBL_model != 'none' and not Cframe:
            absorb = cluster_spectra.get_ebl_absorb(energy.to_value('GeV'), self._redshift, self._EBL_model)
            dN_dEdSdt = dN_dEdSdt * absorb
        
        return energy, dN_dEdSdt.to('GeV-1 cm-2 s-1')
    

    #==================================================
    # Compute gamma ray profile
    #==================================================

    def get_gamma_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                          Emin=None, Emax=None, Energy_density=False,
                          Rmin_los=None, NR500_los=5.0,
                          Cframe=False):
        """
        Compute the gamma ray emission profile within Emin-Emax.
        
        Parameters
        ----------
        - radius (quantity): the projected 2d radius in units homogeneous to kpc, as a 1d array
        - Emin (quantity): the lower bound for gamma ray energy integration
        - Emax (quantity): the upper bound for gamma ray energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - dN_dSdtdO (np.ndarray) : the spectrum in units of cm-2 s-1 sr-1 or GeV cm-2 s-1 sr-1

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')
        
        # Get the integration limits
        if Emin is None:
            Emin = self._Epmin/10.0 # photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define energy and K correction
        eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
        if Cframe:
            eng_rf = eng*1.0
        else:
            eng_rf = eng*(1+self._redshift)

        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dN_dEdVdt = self.get_rate_gamma(eng_rf, r3d)

        # Apply EBL absorbtion
        if self._EBL_model != 'none' and not Cframe:
            absorb = cluster_spectra.get_ebl_absorb(eng.to_value('GeV'), self._redshift, self._EBL_model)
            dN_dEdVdt = dN_dEdVdt * model_tools.replicate_array(absorb, len(r3d), T=True)
            
        # Compute energy integal
        dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)
        
        # Compute integral over l.o.s.
        dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
        dN_dVdt_proj[radius > self._R_truncation] = 0
        
        # Convert to physical to angular scale
        dN_dtdO = dN_dVdt_proj * self._D_ang**2 * u.Unit('sr-1')

        # From intrinsic luminosity to flux
        dN_dSdtdO = dN_dtdO / (4*np.pi * self._D_lum**2)
        
        # return
        if Energy_density:
            dN_dSdtdO = dN_dSdtdO.to('GeV cm-2 s-1 sr-1')
        else :
            dN_dSdtdO = dN_dSdtdO.to('cm-2 s-1 sr-1')
            
        return radius, dN_dSdtdO

    
    #==================================================
    # Compute gamma ray flux
    #==================================================
    
    def get_gamma_flux(self, Emin=None, Emax=None, Energy_density=False,
                       Rmin=None, Rmax=None,
                       type_integral='spherical',
                       Rmin_los=None, NR500_los=5.0,
                       Cframe=False):
        
        """
        Compute the gamma ray emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the gamma ray emmission enclosed within an circular area (i.e.
        cylindrical), and in a given energy band. The minimal energy can be an array to 
        flux(>E) and the radius max can be an array to get flux(<R).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for gamma ray energy integration
        It can be an array.
        - Emax (quantity): the upper bound for gamma ray energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - flux (quantity) : the gamma ray flux either in GeV/cm2/s or ph/cm2/s, depending
        on parameter Energy_density

        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Emin is None:
            Emin = self._Epmin/10.0 # default photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax

        # Check if Emin and Rmax are scalar or array
        if type(Emin.value) == np.ndarray and type(Rmax.value) == np.ndarray:
            raise ValueError('Emin and Rmax cannot both be array simultaneously')

        #----- Case of scalar quantities
        if type(Emin.value) == float and type(Rmax.value) == float:
            # Get a spectrum
            energy = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_gamma_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                        type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

            # Integrate over it and return
            flux = model_tools.energy_integration(dN_dEdSdt, energy, Energy_density=Energy_density)

        #----- Case of energy array
        if type(Emin.value) == np.ndarray:
            # Get a spectrum
            energy = model_tools.sampling_array(np.amin(Emin.value)*Emin.unit, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_gamma_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                        type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

            # Integrate over it and return
            if Energy_density:
                flux = np.zeros(len(Emin))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Emin))*u.Unit('cm-2 s-1')
                
            itpl = interpolate.interp1d(energy.value, dN_dEdSdt.value, kind='linear')
                
            for i in range(len(Emin)):
                eng_i = model_tools.sampling_array(Emin[i], Emax, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dEdSdt_i = itpl(eng_i.value)*dN_dEdSdt.unit
                
                flux[i] = model_tools.energy_integration(dN_dEdSdt_i, eng_i, Energy_density=Energy_density)

        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get energy integration
            eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            if Cframe:
                eng_rf = eng*1.0
            else:
                eng_rf = eng*(1+self._redshift)
                
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_gamma(eng_rf, r3d)

            # Apply EBL absorbtion
            if self._EBL_model != 'none' and not Cframe:
                absorb = cluster_spectra.get_ebl_absorb(eng.to_value('GeV'), self._redshift, self._EBL_model)
                dN_dEdVdt = dN_dEdVdt * model_tools.replicate_array(absorb, len(r3d), T=True)

            # Compute energy integal
            dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)
        
            # Define output
            if Energy_density:
                flux = np.zeros(len(Rmax))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Rmax))*u.Unit('cm-2 s-1')

            # Case of spherical integral: direct volume integration
            if type_integral == 'spherical':
               itpl = interpolate.interp1d(r3d.to_value('kpc'), dN_dVdt.value, kind='linear')
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dN_dVdt_i = itpl(rad_i.to_value('kpc'))*dN_dVdt.unit
                   lum_i = model_tools.spherical_integration(dN_dVdt_i, rad_i)
                   flux[i] =  lum_i / (4*np.pi * self._D_lum**2)
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
                dN_dVdt_proj[radius > self._R_truncation] = 0

                dN_dSdVdt_proj = dN_dVdt_proj / (4*np.pi * self._D_lum**2)
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dN_dSdVdt_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dN_dSdVdt_proj_i = itpl(rad_i.value)*dN_dSdVdt_proj.unit
                    flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dN_dSdVdt_proj_i, rad_i)
        
        # Return
        if Energy_density:
            flux = flux.to('GeV cm-2 s-1')
        else:
            flux = flux.to('cm-2 s-1')
            
        return flux


    #==================================================
    # Compute gamma map
    #==================================================
    def get_gamma_map(self, Emin=None, Emax=None,
                      Rmin_los=None, NR500_los=5.0,
                      Rmin=None, Rmax=None,
                      Energy_density=False, Normalize=False,
                      Cframe=False):
        """
        Compute the gamma ray map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for gamma ray energy integration.
        Has no effect if Normalized is True
        - Emax (quantity): the upper bound for gamma ray energy integration
        Has no effect if Normalized is True
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        Has no effect if Normalized is True
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        gamma_map (np.ndarray) : the map in units of sr-1 or brightness

        """

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_gamma_profile(radius, Emin=Emin, Emax=Emax, Energy_density=Energy_density,
                                                 Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        gamma_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        gamma_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_gamma_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los,
                                       Emin=Emin, Emax=Emax, Energy_density=Energy_density, Cframe=Cframe)
            gamma_map = gamma_map / flux
            gamma_map = gamma_map.to('sr-1')

        else:
            if Energy_density:
                gamma_map = gamma_map.to('GeV cm-2 s-1 sr-1')
            else :
                gamma_map = gamma_map.to('cm-2 s-1 sr-1')
                
        return gamma_map

    
    #==================================================
    # Compute neutrinos spectrum
    #==================================================

    def get_neutrino_spectrum(self, energy=np.logspace(-2,6,100)*u.GeV,
                              Rmin=None, Rmax=None,
                              type_integral='spherical',
                              Rmin_los=None, NR500_los=5.0,
                              flavor='all',
                              Cframe=False):
        """
        Compute the neutrino emission enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the neutrino emmission enclosed within an circular area (i.e.
        cylindrical).
        
        Parameters
        ----------
        - energy (quantity) : the physical energy of neutrinos
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - flavor (str): either 'all', 'numu' or 'nue'
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - energy (quantity) : the physical energy of neutrino
        - dN_dEdSdt (np.ndarray) : the spectrum in units of GeV-1 cm-2 s-1

        """
                
        # In case the input is not an array
        energy = model_tools.check_qarray(energy, unit='GeV')

        # K-correction
        if Cframe:
            energy_rf = energy*1.0
        else:
            energy_rf = energy*(1+self._redshift)
        
        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin
            
        # Compute the integral
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_neutrino(energy_rf, rad, flavor=flavor)
            dN_dEdt = model_tools.spherical_integration(dN_dEdVdt, rad)
            
        # Compute the integral        
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_neutrino(energy_rf, r3d, flavor=flavor)
            dN_dEdt = model_tools.cylindrical_integration(dN_dEdVdt, energy, r3d, r2d, los, Rtrunc=self._R_truncation)
        
        # From intrinsic luminosity to flux
        dN_dEdSdt = dN_dEdt / (4*np.pi * self._D_lum**2)
        
        return energy, dN_dEdSdt.to('GeV-1 cm-2 s-1')
    

    #==================================================
    # Compute neutrino profile
    #==================================================

    def get_neutrino_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                             Emin=None, Emax=None, Energy_density=False,
                             Rmin_los=None, NR500_los=5.0,
                             flavor='all',
                             Cframe=False):
        """
        Compute the neutrino emission profile within Emin-Emax.
        
        Parameters
        ----------
        - radius (quantity): the projected 2d radius in units homogeneous to kpc, as a 1d array
        - Emin (quantity): the lower bound for neutrino energy integration
        - Emax (quantity): the upper bound for neutrino energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - flavor (str): either 'all', 'numu' or 'nue'
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - dN_dSdtdO (np.ndarray) : the spectrum in units of cm-2 s-1 sr-1 or GeV cm-2 s-1 sr-1

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')
        
        # Get the integration limits
        if Emin is None:
            Emin = self._Epmin/10.0 # photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define energy and K correction
        eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
        if Cframe:
            eng_rf = eng*1.0
        else:
            eng_rf = eng*(1+self._redshift)
        
        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dN_dEdVdt = self.get_rate_neutrino(eng_rf, r3d, flavor=flavor)

        # Compute energy integal
        dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)

        # Compute integral over l.o.s.
        dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
        dN_dVdt_proj[radius > self._R_truncation] = 0
        
        # Convert to physical to angular scale
        dN_dtdO = dN_dVdt_proj * self._D_ang**2 * u.Unit('sr-1')

        # From intrinsic luminosity to flux
        dN_dSdtdO = dN_dtdO / (4*np.pi * self._D_lum**2)
        
        # return
        if Energy_density:
            dN_dSdtdO = dN_dSdtdO.to('GeV cm-2 s-1 sr-1')
        else :
            dN_dSdtdO = dN_dSdtdO.to('cm-2 s-1 sr-1')
            
        return radius, dN_dSdtdO


    #==================================================
    # Compute neutrino flux
    #==================================================

    def get_neutrino_flux(self, Emin=None, Emax=None, Energy_density=False,
                          Rmin=None, Rmax=None,
                          type_integral='spherical',
                          Rmin_los=None, NR500_los=5.0,
                          flavor='all',
                          Cframe=False):
        
        """
        Compute the neutrino emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the neutrino emmission enclosed within an circular area (i.e.
        cylindrical), and in a given energy band. The minimal energy can be an array to 
        flux(>E) and the radius max can be an array to get flux(<R).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for neutrino energy integration
        It can be an array.
        - Emax (quantity): the upper bound for neutrino energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - flux (quantity) : the neutrino flux either in GeV/cm2/s or ph/cm2/s, depending
        on parameter Energy_density

        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Emin is None:
            Emin = self._Epmin/10.0 # default photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax

        # Check if Emin and Rmax are scalar or array
        if type(Emin.value) == np.ndarray and type(Rmax.value) == np.ndarray:
            raise ValueError('Emin and Rmax cannot both be array simultaneously')

        #----- Case of scalar quantities
        if type(Emin.value) == float and type(Rmax.value) == float:
            # Get a spectrum
            energy = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_neutrino_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                           type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los,
                                                           flavor=flavor, Cframe=Cframe)

            # Integrate over it and return
            flux = model_tools.energy_integration(dN_dEdSdt, energy, Energy_density=Energy_density)

        #----- Case of energy array
        if type(Emin.value) == np.ndarray:
            # Get a spectrum
            energy = model_tools.sampling_array(np.amin(Emin.value)*Emin.unit, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_neutrino_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                           type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los,
                                                           flavor=flavor, Cframe=Cframe)

            # Integrate over it and return
            if Energy_density:
                flux = np.zeros(len(Emin))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Emin))*u.Unit('cm-2 s-1')
                
            itpl = interpolate.interp1d(energy.value, dN_dEdSdt.value, kind='linear')
                
            for i in range(len(Emin)):
                eng_i = model_tools.sampling_array(Emin[i], Emax, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dEdSdt_i = itpl(eng_i.value)*dN_dEdSdt.unit
                flux[i] = model_tools.energy_integration(dN_dEdSdt_i, eng_i, Energy_density=Energy_density)

        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get energy integration
            eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            if Cframe:
                eng_rf = eng*1.0
            else:
                eng_rf = eng*(1+self._redshift)
            
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_neutrino(eng_rf, r3d)

            # Compute energy integal
            dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)
        
            # Define output
            if Energy_density:
                flux = np.zeros(len(Rmax))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Rmax))*u.Unit('cm-2 s-1')

            # Case of spherical integral: direct volume integration
            if type_integral == 'spherical':
               itpl = interpolate.interp1d(r3d.to_value('kpc'), dN_dVdt.value, kind='linear')
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dN_dVdt_i = itpl(rad_i.to_value('kpc'))*dN_dVdt.unit
                   lum_i = model_tools.spherical_integration(dN_dVdt_i, rad_i)
                   flux[i] =  lum_i / (4*np.pi * self._D_lum**2)
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
                dN_dVdt_proj[radius > self._R_truncation] = 0

                dN_dSdVdt_proj = dN_dVdt_proj / (4*np.pi * self._D_lum**2)
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dN_dSdVdt_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dN_dSdVdt_proj_i = itpl(rad_i.value)*dN_dSdVdt_proj.unit
                    flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dN_dSdVdt_proj_i, rad_i)
        
        # Return
        if Energy_density:
            flux = flux.to('GeV cm-2 s-1')
        else:
            flux = flux.to('cm-2 s-1')
            
        return flux
    

    #==================================================
    # Compute neutrino map
    #==================================================
    def get_neutrino_map(self, Emin=None, Emax=None,
                         Rmin_los=None, NR500_los=5.0,
                         Rmin=None, Rmax=None,
                         Energy_density=False, Normalize=False,
                         flavor='all',
                         Cframe=False):
        """
        Compute the neutrino map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for nu energy integration.
        Has no effect if Normalized is True
        - Emax (quantity): the upper bound for nu energy integration
        Has no effect if Normalized is True
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        Has no effect if Normalized is True
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 
        - flavor (str): either 'all', 'numu' or 'nue'
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        neutrino_map (np.ndarray) : the map in units of sr-1 or brightness

        """

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_neutrino_profile(radius, Emin=Emin, Emax=Emax, Energy_density=Energy_density,
                                                    Rmin_los=Rmin_los, NR500_los=NR500_los, flavor=flavor, Cframe=Cframe)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        nu_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        nu_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_neutrino_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los,
                                          Emin=Emin, Emax=Emax, Energy_density=Energy_density, flavor=flavor, Cframe=Cframe)
            nu_map = nu_map / flux
            nu_map = nu_map.to('sr-1')

        else:
            if Energy_density:
                nu_map = nu_map.to('GeV cm-2 s-1 sr-1')
            else :
                nu_map = nu_map.to('cm-2 s-1 sr-1')
                
        return nu_map

    

    #==================================================
    # Compute inverse compton spectrum
    #==================================================

    def get_ic_spectrum(self, energy=np.logspace(-2,6,100)*u.GeV,
                        Rmin=None, Rmax=None,
                        type_integral='spherical',
                        Rmin_los=None, NR500_los=5.0,
                        Cframe=False):
        """
        Compute the inverse Compton emission enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the inverse Compton emmission enclosed within an circular area (i.e.
        cylindrical).
        
        Note
        ----------
        At high energy, the IC emission analytical parametrization present sharp features 
        which require a rather high NptEePD (10 is clearly to low and will induce wiggles 
        in the spectrum)

        Parameters
        ----------
        - energy (quantity) : the physical energy of photons
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - energy (quantity) : the physical energy of photons
        - dN_dEdSdt (np.ndarray) : the spectrum in units of GeV-1 cm-2 s-1

        """
                
        # In case the input is not an array
        energy = model_tools.check_qarray(energy, unit='GeV')

        # K-correction
        if Cframe:
            energy_rf = energy*1.0
        else:
            energy_rf = energy*(1+self._redshift)
        
        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin
            
        # Compute the integral
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_ic(energy_rf, rad)
            dN_dEdt = model_tools.spherical_integration(dN_dEdVdt, rad)
            
        # Compute the integral        
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_ic(energy_rf, r3d)
            dN_dEdt = model_tools.cylindrical_integration(dN_dEdVdt, energy, r3d, r2d, los, Rtrunc=self._R_truncation)
        
        # From intrinsic luminosity to flux
        dN_dEdSdt = dN_dEdt / (4*np.pi * self._D_lum**2)

        # Apply EBL absorbtion
        if self._EBL_model != 'none' and not Cframe:
            absorb = cluster_spectra.get_ebl_absorb(energy.to_value('GeV'), self._redshift, self._EBL_model)
            dN_dEdSdt = dN_dEdSdt * absorb
        
        return energy, dN_dEdSdt.to('GeV-1 cm-2 s-1')


    #==================================================
    # Compute inverse Compton profile
    #==================================================

    def get_ic_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                       Emin=None, Emax=None, Energy_density=False,
                       Rmin_los=None, NR500_los=5.0,
                       Cframe=False):
        """
        Compute the inverse Compton emission profile within Emin-Emax.
        
        Parameters
        ----------
        - radius (quantity): the projected 2d radius in units homogeneous to kpc, as a 1d array
        - Emin (quantity): the lower bound for IC energy integration
        - Emax (quantity): the upper bound for IC energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - dN_dSdtdO (np.ndarray) : the spectrum in units of cm-2 s-1 sr-1 or GeV cm-2 s-1 sr-1

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')
        
        # Get the integration limits
        if Emin is None:
            Emin = self._Epmin/10.0 # photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define energy and K correction
        eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
        if Cframe:
            eng_rf = eng*1.0
        else:
            eng_rf = eng*(1+self._redshift)
        
        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dN_dEdVdt = self.get_rate_ic(eng_rf, r3d)

        # Apply EBL absorbtion
        if self._EBL_model != 'none' and not Cframe:
            absorb = cluster_spectra.get_ebl_absorb(eng.to_value('GeV'), self._redshift, self._EBL_model)
            dN_dEdVdt = dN_dEdVdt * model_tools.replicate_array(absorb, len(r3d), T=True)
            
        # Compute energy integal
        dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)

        # Compute integral over l.o.s.
        dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
        dN_dVdt_proj[radius > self._R_truncation] = 0
        
        # Convert to physical to angular scale
        dN_dtdO = dN_dVdt_proj * self._D_ang**2 * u.Unit('sr-1')

        # From intrinsic luminosity to flux
        dN_dSdtdO = dN_dtdO / (4*np.pi * self._D_lum**2)
        
        # return
        if Energy_density:
            dN_dSdtdO = dN_dSdtdO.to('GeV cm-2 s-1 sr-1')
        else :
            dN_dSdtdO = dN_dSdtdO.to('cm-2 s-1 sr-1')
            
        return radius, dN_dSdtdO

    #==================================================
    # Compute gamma ray flux
    #==================================================
    
    def get_ic_flux(self, Emin=None, Emax=None, Energy_density=False,
                    Rmin=None, Rmax=None,
                    type_integral='spherical',
                    Rmin_los=None, NR500_los=5.0,
                    Cframe=False):
        
        """
        Compute the inverse Compton emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the inverse Compton emmission enclosed within an circular area (i.e.
        cylindrical), and in a given energy band. The minimal energy can be an array to 
        flux(>E) and the radius max can be an array to get flux(<R).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for IC energy integration
        It can be an array.
        - Emax (quantity): the upper bound for IC energy integration
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - flux (quantity) : the IC flux either in GeV/cm2/s or ph/cm2/s, depending
        on parameter Energy_density

        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Emin is None:
            Emin = self._Epmin/10.0 # default photon energy down to 0.1 minimal proton energy
        if Emax is None:
            Emax = self._Epmax

        # Check if Emin and Rmax are scalar or array
        if type(Emin.value) == np.ndarray and type(Rmax.value) == np.ndarray:
            raise ValueError('Emin and Rmax cannot both be array simultaneously')

        #----- Case of scalar quantities
        if type(Emin.value) == float and type(Rmax.value) == float:
            # Get a spectrum
            energy = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_ic_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                     type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

            # Integrate over it and return
            flux = model_tools.energy_integration(dN_dEdSdt, energy, Energy_density=Energy_density)

        #----- Case of energy array
        if type(Emin.value) == np.ndarray:
            # Get a spectrum
            energy = model_tools.sampling_array(np.amin(Emin.value)*Emin.unit, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            energy, dN_dEdSdt = self.get_ic_spectrum(energy, Rmin=Rmin, Rmax=Rmax,
                                                     type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

            # Integrate over it and return
            if Energy_density:
                flux = np.zeros(len(Emin))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Emin))*u.Unit('cm-2 s-1')
                
            itpl = interpolate.interp1d(energy.value, dN_dEdSdt.value, kind='linear')
                
            for i in range(len(Emin)):
                eng_i = model_tools.sampling_array(Emin[i], Emax, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dEdSdt_i = itpl(eng_i.value)*dN_dEdSdt.unit
                flux[i] = model_tools.energy_integration(dN_dEdSdt_i, eng_i, Energy_density=Energy_density)

        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get energy integration
            eng = model_tools.sampling_array(Emin, Emax, NptPd=self._Npt_per_decade_integ, unit=True)
            if Cframe:
                eng_rf = eng*1.0
            else:
                eng_rf = eng*(1+self._redshift)
            
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_ic(eng_rf, r3d)

            # Apply EBL absorbtion
            if self._EBL_model != 'none' and not Cframe:
                absorb = cluster_spectra.get_ebl_absorb(eng.to_value('GeV'), self._redshift, self._EBL_model)
                dN_dEdVdt = dN_dEdVdt * model_tools.replicate_array(absorb, len(r3d), T=True)

            # Compute energy integal
            dN_dVdt = model_tools.energy_integration(dN_dEdVdt, eng, Energy_density=Energy_density)
        
            # Define output
            if Energy_density:
                flux = np.zeros(len(Rmax))*u.Unit('GeV cm-2 s-1')
            else:
                flux = np.zeros(len(Rmax))*u.Unit('cm-2 s-1')

            # Case of spherical integral: direct volume integration
            if type_integral == 'spherical':
               itpl = interpolate.interp1d(r3d.to_value('kpc'), dN_dVdt.value, kind='linear')
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dN_dVdt_i = itpl(rad_i.to_value('kpc'))*dN_dVdt.unit
                   lum_i = model_tools.spherical_integration(dN_dVdt_i, rad_i)
                   flux[i] =  lum_i / (4*np.pi * self._D_lum**2)
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
                dN_dVdt_proj[radius > self._R_truncation] = 0

                dN_dSdVdt_proj = dN_dVdt_proj / (4*np.pi * self._D_lum**2)
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dN_dSdVdt_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dN_dSdVdt_proj_i = itpl(rad_i.value)*dN_dSdVdt_proj.unit
                    flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dN_dSdVdt_proj_i, rad_i)
        
        # Return
        if Energy_density:
            flux = flux.to('GeV cm-2 s-1')
        else:
            flux = flux.to('cm-2 s-1')
            
        return flux

    
    #==================================================
    # Compute IC map
    #==================================================
    def get_ic_map(self, Emin=None, Emax=None,
                   Rmin_los=None, NR500_los=5.0,
                   Rmin=None, Rmax=None,
                   Energy_density=False, Normalize=False,
                   Cframe=False):
        """
        Compute the inverse Compton map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).
        
        Parameters
        ----------
        - Emin (quantity): the lower bound for IC energy integration.
        Has no effect if Normalized is True
        - Emax (quantity): the upper bound for IC energy integration
        Has no effect if Normalized is True
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Energy_density (bool): if True, then the energy density is computed. Otherwise, 
        the number density is computed.
        Has no effect if Normalized is True
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        ic_map (np.ndarray) : the map in units of sr-1 or brightness

        """

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_ic_profile(radius, Emin=Emin, Emax=Emax, Energy_density=Energy_density,
                                              Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        ic_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        ic_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_ic_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los,
                                       Emin=Emin, Emax=Emax, Energy_density=Energy_density, Cframe=Cframe)
            ic_map = ic_map / flux
            ic_map = ic_map.to('sr-1')

        else:
            if Energy_density:
                ic_map = ic_map.to('GeV cm-2 s-1 sr-1')
            else :
                ic_map = ic_map.to('cm-2 s-1 sr-1')
                
        return ic_map


    #==================================================
    # Compute synchrotron spectrum
    #==================================================

    def get_synchrotron_spectrum(self, frequency=np.logspace(-3,2,100)*u.GHz,
                                 Rmin=None, Rmax=None,
                                 type_integral='spherical',
                                 Rmin_los=None, NR500_los=5.0,
                                 Cframe=False):
        """
        Compute the synchrotron emission enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the synchrotron emmission enclosed within a circular area (i.e.
        cylindrical).
        
        Parameters
        ----------
        - frequency (quantity) : the physical frequency of photons
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - frequency (quantity) : the physical energy of photons
        - dE_dtdfdS (np.ndarray) : the spectrum in units of Jy

        """
        
        # In case the input is not an array
        frequency = model_tools.check_qarray(frequency, unit='GHz')
        energy = (const.h * frequency).to('eV')

        # K-correction
        if Cframe:
            energy_rf = energy*1.0
        else:
            energy_rf = energy*(1+self._redshift)
        
        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin
            
        # Compute the integral
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_synchrotron(energy_rf, rad)
            dN_dEdt = model_tools.spherical_integration(dN_dEdVdt, rad)
            
        # Compute the integral        
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dEdVdt = self.get_rate_synchrotron(energy_rf, r3d)
            dN_dEdt = model_tools.cylindrical_integration(dN_dEdVdt, energy, r3d, r2d, los, Rtrunc=self._R_truncation)
            
        # From intrinsic luminosity to flux
        dN_dEdSdt = dN_dEdt / (4*np.pi * self._D_lum**2)
        
        return frequency, (dN_dEdSdt * energy**2 / frequency).to('Jy')
    

    #==================================================
    # Compute synchrotron profile
    #==================================================

    def get_synchrotron_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                                freq0=1*u.GHz,
                                Rmin_los=None, NR500_los=5.0,
                                Cframe=False):
        """
        Compute the synchrotron emission profile at frequency freq0.
        
        Parameters
        ----------
        - radius (quantity): the projected 2d radius in units homogeneous to kpc, as a 1d array
        - freq0 (quantity): the frequency at which the profile is computed
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - sed (np.ndarray) : the spectrum in units of Jy/sr

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')
        
        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define energy and K correction
        eng0 = (freq0 * const.h).to('eV')
        if Cframe:
            eng0_rf = eng0*1.0
        else:
            eng0_rf = eng0*(1+self._redshift)

        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dN_dVdt_E = self.get_rate_synchrotron(eng0_rf, r3d).flatten()
        
        # Compute integral over l.o.s.
        dN_dVdt_E_proj = model_tools.los_integration_1dfunc(dN_dVdt_E, r3d, radius, los)
        dN_dVdt_E_proj[radius > self._R_truncation] = 0
        
        # Convert to physical to angular scale
        dN_dtdO_E = dN_dVdt_E_proj * self._D_ang**2 * u.Unit('sr-1')

        # From intrinsic luminosity to flux
        dN_dSdtdO_E = dN_dtdO_E / (4*np.pi * self._D_lum**2)
        
        # return
        sed = (dN_dSdtdO_E * eng0**2/freq0).to('Jy sr-1')
            
        return radius, sed


    #==================================================
    # Compute synchrotron flux
    #==================================================
    
    def get_synchrotron_flux(self, freq0=1*u.GHz,
                             Rmin=None, Rmax=None,
                             type_integral='spherical',
                             Rmin_los=None, NR500_los=5.0,
                             Cframe=False):
        
        """
        Compute the synchrotron emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the synchrotron emmission enclosed within a circular area (i.e.
        cylindrical), and at a given frequency. The radius max can be an array to get flux(<R).
        
        Parameters
        ----------
        - freq0 (quantity): the frequency at which the profile is computed
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - flux (quantity) : the synchrotron flux in Jy

        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500

        #----- Case of scalar quantities
        if type(Rmax.value) == float:
            freq0, flux = self.get_synchrotron_spectrum(freq0, Rmin=Rmin, Rmax=Rmax,
                                                        type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)
        
        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get frequency sampling
            eng0 = (freq0 * const.h).to('eV')
            if Cframe:
                eng0_rf = eng0*1.0
            else:
                eng0_rf = eng0*(1+self._redshift)
            
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dVdt_E = self.get_rate_synchrotron(eng0_rf, r3d).flatten()

            # Define output
            flux = np.zeros(len(Rmax))*u.Unit('Jy')

            # Case of spherical integral: direct volume integration
            itpl = interpolate.interp1d(r3d.to_value('kpc'), dN_dVdt_E.value, kind='linear')
            if type_integral == 'spherical':
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dN_dVdt_E_i = itpl(rad_i.to_value('kpc'))*dN_dVdt_E.unit
                   lum_i = model_tools.spherical_integration(dN_dVdt_E_i, rad_i) * eng0**2/freq0
                   flux[i] =  lum_i / (4*np.pi * self._D_lum**2)
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dVdt_E_proj = model_tools.los_integration_1dfunc(dN_dVdt_E, r3d, radius, los)
                dN_dVdt_E_proj[radius > self._R_truncation] = 0

                dN_dSdVdt_E_proj = dN_dVdt_E_proj / (4*np.pi * self._D_lum**2)
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dN_dSdVdt_E_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dN_dSdVdt_E_proj_i = itpl(rad_i.value)*dN_dSdVdt_E_proj.unit
                    flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dN_dSdVdt_E_proj_i, rad_i) * eng0**2/freq0
        
        return flux.to('Jy')


    #==================================================
    # Compute synchrotron map
    #==================================================
    def get_synchrotron_map(self, freq0=1*u.GHz,
                            Rmin_los=None, NR500_los=5.0,
                            Rmin=None, Rmax=None,
                            Normalize=False,
                            Cframe=False):
        """
        Compute the synchrotron map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).
        
        Parameters
        ----------
        - freq0 (quantity): the frequency at wich we work
        Has no effect if Normalized is True
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        synchrotron_map (np.ndarray) : the map in units of sr-1 or brightness

        """

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_synchrotron_profile(radius, freq0=freq0, 
                                                       Rmin_los=Rmin_los, NR500_los=NR500_los, Cframe=Cframe)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        synchrotron_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        synchrotron_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_synchrotron_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los, freq0=freq0, Cframe=Cframe)
            synchrotron_map = synchrotron_map / flux
            synchrotron_map = synchrotron_map.to('sr-1')

        else:
            synchrotron_map = synchrotron_map.to('Jy sr-1')
                
        return synchrotron_map

    
    #==================================================
    # Compute SZ spectrum
    #==================================================

    def get_sz_spectrum(self, frequency=np.logspace(1,3,100)*u.GHz, Compton_only=False, 
                        Rmin=None, Rmax=None,
                        type_integral='spherical',
                        Rmin_los=None, NR500_los=5.0):
        """
        Compute the SZ emission enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the SZ emmission enclosed within a circular area (i.e.
        cylindrical).
        
        Parameters
        ----------
        - frequency (quantity) : the physical frequency of photons
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case

        Outputs
        ----------
        - frequency (quantity) : the physical energy of photons
        - dE_dtdfdS (np.ndarray) : the spectrum in units of Jy
        
        """
        
        # In case the input is not an array
        frequency = model_tools.check_qarray(frequency, unit='GHz')

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin
            
        # Compute the integral
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dE_dtdVdfdO_f = self.get_rate_sz(frequency, rad, Compton_only=Compton_only)
            dE_dtdfdO_f = model_tools.spherical_integration(dE_dtdVdfdO_f, rad)
            
        # Compute the integral        
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            dE_dtdVdfdO_f = self.get_rate_sz(frequency, r3d, Compton_only=Compton_only)
            dE_dtdfdO_f = model_tools.cylindrical_integration(dE_dtdVdfdO_f, frequency, r3d, r2d, los, Rtrunc=self._R_truncation)
        
        # return
        if Compton_only:
            output = dE_dtdfdO_f.to('kpc2')
        else:
            dE_dtdf_f = dE_dtdfdO_f / self._D_ang**2 * u.sr # This is because for SZ we want \int S_SZ dOmega, not \int S_SZ dS
            output = dE_dtdf_f.to('Jy')
                        
        return frequency, output

    
    #==================================================
    # Compute SZ profile
    #==================================================

    def get_sz_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                       freq0=100*u.GHz, Compton_only=False, 
                       Rmin_los=None, NR500_los=5.0):
        """
        Get the SZ parameter profile.
        
        Parameters
        ----------
        - radius (quantity): the physical 2d radius in units homogeneous to kpc, as a 1d array
        - freq0 (quantity): the frequency at which the profile is computed.
        - Compton (bool): if set to true, return the Compton-y parameter.
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - Compton_only (bool): Output the Compton parameter instead of the spectrum. In the case of
        Compton only, the frequency input does not matter 

        Outputs
        ----------
        - radius (quantity): the projected 2d radius in unit of kpc
        - output : the Compton parameter or brightness profile

        Note
        ----------
        The pressure profile is truncated at R500 along the line-of-sight.

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')
        
        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dE_dtdVdfdO_f = self.get_rate_sz(freq0, r3d, Compton_only=Compton_only).flatten() 

        # Compute integral over l.o.s.
        dE_dtdSdfdO_f = model_tools.los_integration_1dfunc(dE_dtdVdfdO_f, r3d, radius, los)
        dE_dtdSdfdO_f[radius > self._R_truncation] = 0
        
        # return
        if Compton_only:
            output = dE_dtdSdfdO_f.to_value('')*u.adu
        else:
            output = dE_dtdSdfdO_f.to('Jy sr-1')

        return radius, output
    

    #==================================================
    # Compute SZ flux
    #==================================================
    
    def get_sz_flux(self, freq0=100*u.GHz, Compton_only=False,
                    Rmin=None, Rmax=None,
                    type_integral='spherical',
                    Rmin_los=None, NR500_los=5.0):
        
        """
        Compute the SZ emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the SZ emmission enclosed within a circular area (i.e.
        cylindrical), and at a given frequency (or in Compton unit). The 
        radius max can be an array to get flux(<R).
        
        Parameters
        ----------
        - freq0 (quantity): the frequency at which the profile is computed
        - Compton_only (bool): Output the Compton parameter instead of the spectrum. In the case of
        Compton only, the frequency input does not matter 
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case

        Outputs
        ----------
        - flux (quantity) : the synchrotron flux in Jy or kpc^2 (for Compton)

        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        
        #----- Case of scalar quantities
        if type(Rmax.value) == float:
                freq0, flux = self.get_sz_spectrum(freq0, Compton_only=Compton_only, Rmin=Rmin, Rmax=Rmax,
                                                   type_integral=type_integral, Rmin_los=Rmin_los, NR500_los=NR500_los)
        
        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get frequency sampling
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dE_dtdVdfdO_f = self.get_rate_sz(freq0, r3d, Compton_only=Compton_only).flatten()

            # Define output
            if Compton_only:
                flux = np.zeros(len(Rmax))*u.Unit('kpc2')
            else:
                flux = np.zeros(len(Rmax))*u.Unit('Jy')

            # Case of spherical integral: direct volume integration
            itpl = interpolate.interp1d(r3d.to_value('kpc'), dE_dtdVdfdO_f.value, kind='linear')
            if type_integral == 'spherical':
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dE_dtdVdfdO_f_i = itpl(rad_i.to_value('kpc'))*dE_dtdVdfdO_f.unit
                   if Compton_only:
                       flux[i] = model_tools.spherical_integration(dE_dtdVdfdO_f_i, rad_i)
                   else:
                       flux[i] = model_tools.spherical_integration(dE_dtdVdfdO_f_i, rad_i) / self._D_ang**2*u.sr
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dE_dtdVdfdO_f_proj = model_tools.los_integration_1dfunc(dE_dtdVdfdO_f, r3d, radius, los)
                dE_dtdVdfdO_f_proj[radius > self._R_truncation] = 0
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dE_dtdVdfdO_f_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dE_dtdVdfdO_f_proj_i = itpl(rad_i.value)*dE_dtdVdfdO_f_proj.unit
                    if Compton_only:
                        flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dE_dtdVdfdO_f_proj_i, rad_i)
                    else:
                        flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dE_dtdVdfdO_f_proj_i, rad_i) / self._D_ang**2*u.sr

        # output
        if Compton_only:
            output = flux.to('kpc2')
        else:
            output = flux.to('Jy')
                       
        return output


    #==================================================
    # Compute SZ map
    #==================================================
    def get_sz_map(self, freq0=100*u.GHz, Compton_only=False,
                   Rmin_los=None, NR500_los=5.0,
                   Rmin=None, Rmax=None,
                   Normalize=False):
        """
        Compute the SZ map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).
        
        Parameters
        ----------
        - freq0 (quantity): the frequency at wich we work
        Has no effect if Normalized is True
        - Compton_only (bool): Output the Compton parameter instead of the spectrum. In the case of
        Compton only, the frequency input does not matter 
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 

        Outputs
        ----------
        sz_map (np.ndarray) : the map in units of sr-1 or brightness, or Compton

        """

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_sz_profile(radius, freq0=freq0, Compton_only=Compton_only,
                                              Rmin_los=Rmin_los, NR500_los=NR500_los)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        sz_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        sz_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_sz_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los,
                                    freq0=freq0, Compton_only=Compton_only)
            if Compton_only:
                sz_map = sz_map.to_value('adu') / (flux/self._D_ang**2*u.sr)
                sz_map = sz_map.to('sr-1')
            else:
                sz_map = sz_map / flux
                sz_map = sz_map.to('sr-1')
        else:
            if Compton_only:
                sz_map = sz_map.to('adu')
            else:
                sz_map = sz_map.to('Jy sr-1')
                
        return sz_map

    
    #==================================================
    # Compute Xray spectrum
    #==================================================
    
    def get_xray_spectrum(self, energy=np.linspace(0.1,50,100)*u.keV, 
                          Rmin=None, Rmax=None, 
                          type_integral='spherical',
                          Rmin_los=None, NR500_los=5.0,
                          output_type='C',
                          nH=0.0*u.cm**-2,
                          model='APEC',
                          resp_file=None,
                          data_file=None,
                          Cframe=False):
        """
        Compute the X-ray spectrum enclosed within [Rmin,Rmax], in 3d (i.e. spherically 
        integrated), or the SZ emmission enclosed within a circular area (i.e.
        cylindrical). The emission is computed for a mean temperature.
        
        Parameters
        ----------
        - energy (quantity) : the physical energy of photons
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, R500)
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - output_type (str): type of output
        S == energy counts in erg/s/cm^2/sr
        C == counts in ph/s/cm^2/sr
        R == count rate in ph/s/sr (accounting for instrumental response)
        - nH (quantity): hydrogen column density (homogeneous to cm**-2)
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - energy (quantity) : the physical energy of photons at the center of the bin
        - dN_dtdSdE (np.ndarray) : the spectrum in units of s-1 cm-2 keV-1
        
        """
        
        # In case the input is not an array
        energy = model_tools.check_qarray(energy, unit='keV')

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Get the integration limits
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500
        if Rmin_los is None:
            Rmin_los = self._Rmin

        # Get useful quantity
        mu_gas, mu_e, mu_p, mu_alpha = cluster_global.mean_molecular_weight(Y=self._helium_mass_fraction,
                                                                            Z=self._metallicity_sol*self._abundance)
        
        # Get a mean temperature
        if type_integral == 'spherical':
            rad = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            rad, temperature = self.get_temperature_gas_profile(rad)
            rad, n_e = self.get_density_gas_profile(rad)
            Tmean = model_tools.spherical_integration(temperature, rad) / (4.0/3*np.pi*Rmax**3)
            N2int = model_tools.spherical_integration(n_e**2*mu_e/mu_p, rad)
            
        if type_integral == 'cylindrical':
            Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)
            Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
            r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            r2d = model_tools.sampling_array(Rmin, Rmax, NptPd=self._Npt_per_decade_integ, unit=True)
            rad, temperature = self.get_temperature_gas_profile(r3d)
            temperature[temperature/temperature != 1] = 0
            rad, n_e = self.get_density_gas_profile(r3d)
            temperature_proj = model_tools.los_integration_1dfunc(temperature, r3d, r2d, los)
            temperature_pproj = model_tools.trapz_loglog(2*np.pi*r2d*temperature_proj, r2d)
            Tmean = temperature_pproj/(2*Rmax3d * np.pi*Rmax**2)
            n_e2_proj = model_tools.los_integration_1dfunc(n_e**2*mu_e/mu_p, r3d, r2d, los)
            N2int = model_tools.trapz_loglog(2*np.pi*r2d*n_e2_proj, r2d)
            
        # Get the spectrum normalized to 1 cm-5
        if Cframe:
            z_xspec = 0.0
        else:
            z_xspec = self._redshift
            
        dSB, dNph, dR, ectr, epot = cluster_xspec.xray_spectrum(nH.to_value('cm-2')*1e-22,
                                                                Tmean.to_value('keV'),
                                                                self._abundance,
                                                                z_xspec,
                                                                emin=np.amin(energy.to_value('keV')),
                                                                emax=np.amax(energy.to_value('keV')),
                                                                nbin=len(energy),
                                                                file_ana='./xspec_analysis.txt',
                                                                file_out='./xspec_analysis_output.txt',
                                                                model=model,
                                                                resp_file=resp_file,
                                                                data_file=data_file,
                                                                cleanup=True, logspace=True)

        # Normalization
        xspec_norm = (1e-14/(4*np.pi*self._D_ang**2*(1+self._redshift)**2) * N2int).to_value('cm-5')
        
        # return
        if output_type == 'S':
            output = dSB  * xspec_norm * u.Unit('erg s-1 cm-2 keV-1')
        if output_type == 'C':
            output = dNph * xspec_norm * u.Unit('s-1 cm-2 keV-1')
        if output_type == 'R':
            output = dR  * xspec_norm  * u.Unit('s-1 keV-1')
                        
        return ectr*u.keV, output


    #==================================================
    # Compute Xray profile
    #==================================================

    def get_xray_profile(self, radius=np.logspace(0,4,100)*u.kpc,
                         Rmin_los=None, NR500_los=5.0,
                         output_type='C',
                         Cframe=False):
        
        """
        Get the Xray surface brightness profile. An xspec table file is needed as 
        output_dir+'/XSPEC_table.txt'. The energy band is defined in this file.
        
        Parameters
        ----------
        - radius (quantity): the physical 2d radius in units homogeneous to kpc, as a 1d array
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        - output_type (str): type of output
        S == energy counts in erg/s/cm^2/sr
        C == counts in ph/s/cm^2/sr
        R == count rate in ph/s/sr (accounting for instrumental response)
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - radius (quantity): the projected 2d radius in unit of kpc
        - output : the brightness profile, depending on output_type

        Note
        ----------
        The pressure profile is truncated at R500 along the line-of-sight.

        """
        
        # In case the input is not an array
        radius = model_tools.check_qarray(radius, unit='kpc')

        # Check output type
        output_list = ['S', 'C', 'R']
        if output_type not in output_list:
            raise ValueError("Available output_type are S, C and R.")        
        
        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        Rmin = np.amin(radius.to_value('kpc'))*u.kpc
        Rmax = np.amax(radius.to_value('kpc'))*u.kpc

        # Define array for integration
        Rmax3d = np.sqrt((NR500_los*self._R500)**2 + Rmax**2)        
        Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)
        r3d = model_tools.sampling_array(Rmin3d*0.9, Rmax3d*1.1, NptPd=self._Npt_per_decade_integ, unit=True)
        los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
        dN_dVdt = self.get_rate_xray(r3d, output_type=output_type, Cframe=Cframe).flatten()
        
        # Compute integral over l.o.s.
        dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
        dN_dVdt_proj[radius > self._R_truncation] = 0

        # Convert to physical to angular scale
        dN_dtdO = dN_dVdt_proj * self._D_ang**2 * u.Unit('sr-1')

        # From intrinsic luminosity to flux
        dN_dSdtdO = dN_dtdO / (4*np.pi * self._D_lum**2)
        
        # return
        if output_type == 'S':
            output = dN_dSdtdO.to('erg s-1 cm-2 sr-1')
        if output_type == 'C':
            output = dN_dSdtdO.to('s-1 cm-2 sr-1')
        if output_type == 'R':
            output = dN_dSdtdO.to('s-1 sr-1')

        return radius, output


    #==================================================
    # Compute Xray flux
    #==================================================
    
    def get_xray_flux(self, Rmin=None, Rmax=None,
                      type_integral='spherical',
                      Rmin_los=None, NR500_los=5.0,
                      output_type='C',
                      Cframe=False):
        
        """
        Compute the Xray emission enclosed within Rmax, in 3d (i.e. spherically 
        integrated), or the Xray emmission enclosed within a circular area (i.e.
        cylindrical), and in a given band depending on Xspec file. The radius 
        max can be an array to get flux(<R).

        Parameters
        ----------
        - Rmin (quantity): the minimal radius within with the spectrum is computed 
        - Rmax (quantity): the maximal radius within with the spectrum is computed.
        It can be an array.
        - type_integral (string): either 'spherical' or 'cylindrical'
        - Rmin_los (quantity): minimal radius at which l.o.s integration starts
        This is used only for cylindrical case
        - NR500_los (float): the line-of-sight integration will stop at NR500_los x R500. 
        This is used only for cylindrical case
        - output_type (str): type of output
        S == energy counts in erg/s/cm^2/sr
        C == counts in ph/s/cm^2/sr
        R == count rate in ph/s/sr (accounting for instrumental response)
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        - flux (quantity) : the Xray flux in erg s-1 cm-2 or s-1 cm-2 or s-1 
        (depending on output_type)


        """

        # Check the type of integral
        ok_list = ['spherical', 'cylindrical']
        if not type_integral in ok_list:
            raise ValueError("This requested integral type (type_integral) is not available")

        # Check output type
        output_list = ['S', 'C', 'R']
        if output_type not in output_list:
            raise ValueError("Available output_type are S, C and R.")        
        
        # Get the integration limits
        if Rmin_los is None:
            Rmin_los = self._Rmin
        if Rmin is None:
            Rmin = self._Rmin
        if Rmax is None:
            Rmax = self._R500

        #----- Case of scalar quantities
        scalar_flag = False
        if type(Rmax.value) == float:
            scalar_flag = True
            Rmax = np.tile(Rmax, [1]) # replicate Rmax to make it as an array
        
        #----- Case of radius array (need to use dN/dVdEdt and not get_profile because spherical flux)
        if type(Rmax.value) == np.ndarray:
            # Get frequency sampling
            if type_integral == 'spherical':
                Rmax3d = np.amax(Rmax.value)*Rmax.unit
                Rmin3d = Rmin
            if type_integral == 'cylindrical':
                Rmax3d = np.sqrt((NR500_los*self._R500)**2 + (np.amax(Rmax.value)*Rmax.unit)**2)*1.1        
                Rmin3d = np.sqrt(Rmin_los**2 + Rmin**2)*0.9
            r3d = model_tools.sampling_array(Rmin3d, Rmax3d, NptPd=self._Npt_per_decade_integ, unit=True)
            los = model_tools.sampling_array(Rmin_los, NR500_los*self._R500, NptPd=self._Npt_per_decade_integ, unit=True)
            dN_dVdt = self.get_rate_xray(r3d, output_type=output_type, Cframe=Cframe).flatten()
            
            # Define output
            if output_type == 'S':
                flux = np.zeros(len(Rmax))*u.Unit('erg s-1 cm-2')
            if output_type == 'C':
                flux = np.zeros(len(Rmax))*u.Unit('s-1 cm-2')
            if output_type == 'R':
                flux = np.zeros(len(Rmax))*u.Unit('s-1')

            # Case of spherical integral: direct volume integration
            itpl = interpolate.interp1d(r3d.to_value('kpc'), dN_dVdt.value, kind='linear')
            if type_integral == 'spherical':
               for i in range(len(Rmax)):
                   rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                   dN_dVdt_i = itpl(rad_i.to_value('kpc'))*dN_dVdt.unit
                   lum_i = model_tools.spherical_integration(dN_dVdt_i, rad_i)
                   flux[i] =  lum_i / (4*np.pi * self._D_lum**2)
                
            # Case of cylindrical integral
            if type_integral == 'cylindrical':
                # Compute integral over l.o.s.
                radius = model_tools.sampling_array(Rmin, np.amax(Rmax.value)*Rmax.unit, NptPd=self._Npt_per_decade_integ, unit=True)
                dN_dVdt_proj = model_tools.los_integration_1dfunc(dN_dVdt, r3d, radius, los)
                dN_dVdt_proj[radius > self._R_truncation] = 0

                dN_dSdVdt_proj = dN_dVdt_proj / (4*np.pi * self._D_lum**2)
        
                itpl = interpolate.interp1d(radius.to_value('kpc'), dN_dSdVdt_proj.value, kind='linear')
                
                for i in range(len(Rmax)):
                    rad_i = model_tools.sampling_array(Rmin, Rmax[i], NptPd=self._Npt_per_decade_integ, unit=True)
                    dN_dSdVdt_proj_i = itpl(rad_i.value)*dN_dSdVdt_proj.unit
                    flux[i] = model_tools.trapz_loglog(2*np.pi*rad_i*dN_dSdVdt_proj_i, rad_i)

        # Define output
        if scalar_flag:
            flux = flux[0] # to return a scalar
        
        if output_type == 'S':
            output = flux.to('erg s-1 cm-2')
        if output_type == 'C':
            output = flux.to('s-1 cm-2')
        if output_type == 'R':
            output = flux.to('s-1')
        
        return flux


    #==================================================
    # Compute Xray map
    #==================================================
    def get_xray_map(self, Rmin_los=None, NR500_los=5.0,
                     Rmin=None, Rmax=None,
                     Normalize=False,
                     output_type='C',
                     Cframe=False):
        """
        Compute the Xray map. The map is normalized so that the integral 
        of the map over the cluster volume is 1 (up to Rmax=5R500).

        Parameters
        ----------
        - Rmin_los (Quantity): the radius at which line of sight integration starts
        - NR500_los (float): the integration will stop at NR500_los x R500
        - Rmin, Rmax (quantity): the radius within with the spectrum is computed 
        (default is 1kpc, Rtruncation) for getting the normlization flux.
        Has no effect if Normalized is False
        - Normalize (bool): if True, the map is normalized by the flux to get a 
        template in unit of sr-1 
        - output_type (str): type of output
        S == energy counts in erg/s/cm^2/sr
        C == counts in ph/s/cm^2/sr
        R == count rate in ph/s/sr (accounting for instrumental response)
        - Cframe (bool): computation assumes that we are in the cluster frame (no redshift effect)

        Outputs
        ----------
        synchrotron_map (np.ndarray) : the map in units of sr-1 or brightness

        """

        # Check output type
        output_list = ['S', 'C', 'R']
        if output_type not in output_list:
            raise ValueError("Available output_type are S, C and R.")        

        # Get the header
        header = self.get_map_header()

        # Get a R.A-Dec. map
        ra_map, dec_map = map_tools.get_radec_map(header)

        # Get a cluster distance map (in deg)
        dist_map = map_tools.greatcircle(ra_map, dec_map, self._coord.icrs.ra.to_value('deg'), self._coord.icrs.dec.to_value('deg'))
        
        # Define the radius used fo computing the profile
        theta_max = np.amax(dist_map) # maximum angle from the cluster
        theta_min = np.amin(dist_map) # minimum angle from the cluster (~0 if cluster within FoV)
        if theta_min > 10 and theta_max > 10:
            print('!!!!! WARNING: the cluster location is very much offset from the field of view')
        rmax = theta_max*np.pi/180 * self._D_ang
        rmin = theta_min*np.pi/180 * self._D_ang
        radius = model_tools.sampling_array(rmin, rmax, NptPd=self._Npt_per_decade_integ, unit=True)
        
        # Project the integrand
        r_proj, profile = self.get_xray_profile(radius, Rmin_los=Rmin_los, NR500_los=NR500_los, output_type=output_type, Cframe=Cframe)

        # Convert to angle and interpolate onto a map
        theta_proj = (r_proj/self._D_ang).to_value('')*180.0/np.pi   # degrees
        xray_map = map_tools.profile2map(profile.value, theta_proj, dist_map)*profile.unit
        
        # Avoid numerical residual ringing from interpolation
        xray_map[dist_map > self._theta_truncation.to_value('deg')] = 0
        
        # Compute the normalization: to return a map in sr-1, i.e. by computing the total flux
        if Normalize:
            if Rmax is None:
                if self._R_truncation is not np.inf:
                    Rmax = self._R_truncation
                else:                    
                    Rmax = NR500_los*self._R500
            if Rmin is None:
                Rmin = self._Rmin
            flux = self.get_xray_flux(Rmin=Rmin, Rmax=Rmax, type_integral='cylindrical', NR500_los=NR500_los, output_type=output_type, Cframe=Cframe)
            xray_map = xray_map / flux
            xray_map = xray_map.to('sr-1')
        else:
            if output_type == 'S':
                xray_map = xray_map.to('erg s-1 cm-2 sr-1')
            if output_type == 'C':
                xray_map = xray_map.to('s-1 cm-2 sr-1')
            if output_type == 'R':
                xray_map = xray_map.to('s-1 sr-1')
            
        return xray_map
    
