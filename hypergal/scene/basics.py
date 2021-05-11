
from ..utils import geometry
import numpy as np
#import warnings

DEFAULT_SCALE_RATIO = 0.558/0.25 #SEDm/PS1


# ================= #
#                   #
#   SLICE SCENE     # 
#                   #
# ================= #
class SliceScene( object ):

    BASE_PARAMETERS = ["ampl", "background"]
    
    def __init__(self, slice_in, slice_comp, xy_in=None, xy_comp=None, load_overlay=True,
                     psf=None, **kwargs):
        """ """
        self.set_slice(slice_in, "in")
        self.set_slice(slice_comp, "comp")
        
        if load_overlay:
            self.load_overlay(xy_in=xy_in, xy_comp=xy_comp, **kwargs)
            
        if psf is not None:
            self.set_psf(psf)
            
    @classmethod
    def from_slices(cls, slice_in, slice_comp, xy_in=None, xy_comp=None, psf=None, **kwargs):
        """ """
        return cls(slice_in, slice_comp,
                       xy_in=xy_in, xy_comp=xy_comp, psf=psf,
                       **kwargs)

    # ============= #
    #  Methods      #
    # ============= #
    def load_overlay(self,  xy_in=None, xy_comp=None, 
                       rotation_in=None, rotation_comp=None,
                       scale_in=None, scale_comp=DEFAULT_SCALE_RATIO):
        """ """
        # get all the inputs and drop the self.
        klocal = locals()
        _ = klocal.pop("self")
        overlay = geometry.Overlay.from_slices(self.slice_in, self.slice_comp,
                                                **klocal)
        self.set_overlay(overlay)
        
    # --------- #
    #  SETTER   #
    # --------- #
    def set_slice(self, slice_, which, norm="nanmean"):
        """ set the 'in' or 'comp' geometry
        
        Parameters
        ----------
        slice: [pyifu.Slice]
            spaxelhandler object (Slice)

        which: [string]
            Which geometry are you providing ?
            - in or which.
            a ValueError is raise if which is not 'in' or 'comp'

        Returns
        -------
        None
        """
        if type(norm) is str:
            norm = getattr(np, norm)(slice_.data, axis=0)
            
        if which == "in":
            self._slice_in = slice_
            self._norm_in = norm
            self._flux_in = slice_.data/norm
            nshape = int(np.sqrt(len(self._flux_in)))
            self._flux_in2d = self._flux_in.reshape(nshape,nshape)
            if slice_.has_variance():
                self._variance_in = slice_.variance/norm**2
            else:
                self._variance_in = None
                
        elif which == "comp":
            self._slice_comp = slice_
            self._norm_comp = norm
            self._flux_comp = slice_.data/norm
            if slice_.has_variance():
                self._variance_comp = slice_.variance/norm**2
            else:
                self._variance_comp = None
            
        else:
            raise ValueError(f"which can be 'in' or 'comp', {which} given")

    def set_overlay(self, overlay):
        """ Provide the hypergal.utils.geometry.Overlay object """
        self._overlay = overlay

    def set_psf(self, psf):
        """ """
        self._psf = psf
        
    # --------- #
    #  GETTER   #
    # --------- #
    def get_model(self, ampl=1, background=0,
                      overlayparam=None,
                      psfparam=None):
        """ Convolves and project flux_in into the 


        Parameters
        ----------
        overlayparam: [dict or None]
            if dict, this is passed as kwargs to overlay
        psfparam: [dict or None]
            if dict, this is passed as a kwargs to self.psf.update_parameters(**psfparam)

        Returns
        -------
        flux
        """
        # 1.
        # Change position of the comp grid if needed
        #   - if the overlayparam are the same as already know, no update made.
        if overlayparam is not None and len(overlayparam)>0:
            self.overlay.change_comp(**overlayparam)

        # 2.            
        # Change values of flux and variances of _in by convolving the image
        flux_in = self.get_convolved_flux_in(psfparam)

        # 3. (overlaydf calculated only if needed)
        # Get the new projected flux and variance (_in->_comp grid)
        modelflux = self.overlay.get_projected_flux(flux_in)

        # 4. Out
        return ampl*modelflux + background
    
    def get_convolved_flux_in(self, psfconv):
        """ """
        if psfconv is None or len(psfconv)==0:
            return self.flux_in
        
        self.psf.update_parameters(**psfconv)
        return self.psf.convolve(self._flux_in2d).flatten()

    def guess_parameters(self):
        """ """
        bkgd_in = np.percentile(self.flux_in, 10)
        bkgd_comp = np.percentile(self.flux_comp, 10)
        flux_ratio = (np.nansum(self.flux_comp)-bkgd_comp) / (np.nansum(self.flux_in)-bkgd_in)

        base_guess = {**{k:None for k in self.BASE_PARAMETERS},
                      **{"ampl":flux_ratio, "background": bkgd_comp-flux_ratio*bkgd_in}
                      }
        geom_guess = self.overlay.geoparam_comp
        psf_guess  = self.psf.guess_parameters()
        return {**base_guess, **geom_guess, **psf_guess}
         
    # ============= #
    #  Properties   #
    # ============= #
    @property
    def slice_in(self):
        """ """
        return self._slice_in
    
    @property    
    def slice_comp(self):
        """ """
        return self._slice_comp

    @property
    def overlay(self):
        """ """
        if not hasattr(self,"_overlay"):
            raise AttributeError("No Overlay set ; see self.set/load_overlay()")
        return self._overlay

    @property
    def psf(self):
        """ """
        if not hasattr(self, "_psf"):
            raise AttributeError("No PSF set ; see self.set_psf()")
        
        return self._psf

    @property
    def norm_in(self):
        """ """ # No test to gain time
        return self._norm_in
    
    @property
    def norm_comp(self):
        """ """ # No test to gain time
        return self._norm_in

    @property
    def norm_comp(self):
        """ """ # No test to gain time
        return self._flux_comp

    @property
    def flux_in(self):
        """ """ # No test to gain time
        return self._flux_in

    @property
    def flux_comp(self):
        """ """ # No test to gain time
        return self._flux_comp
    
    @property
    def variance_in(self):
        """ """ # No test to gain time
        return self._variance_in

    @property
    def variance_comp(self):
        """ """ # No test to gain time
        return self._variance_comp

    # ----------- #
    #  Parameters #
    # ----------- #
    @property
    def PSF_PARAMETERS(self):
        """ """
        return self.psf.PARAMETER_NAMES
    
    @property
    def GEOMETRY_PARAMETERS(self):
        """ """
        return self.overlay.PARAMETER_NAMES
    
    @property
    def PARAMETER_NAMES(self):
        """ """
        return self.BASE_PARAMETERS + self.GEOMETRY_PARAMETERS + self.PSF_PARAMETERS
    
# ================= #
#                   #
#   CUBE SCENE      # 
#                   #
# ================= #

class CubeScene( SliceScene ):
    def __init__(self, *args, **kwargs):
        """ """
        _ = super().__init__(*args, **kwargs)
        print("CubeScene has not been implemented yet")
        