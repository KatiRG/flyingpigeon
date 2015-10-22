from malleefowl.process import WPSProcess

from malleefowl import wpslogging as logging
logger = logging.getLogger(__name__)

class modelUncertainty(WPSProcess):
    def __init__(self):
        # definition of this process
        WPSProcess.__init__(self, 
            identifier = "modelUncertainty",
            title="Robustness of modelled signal changes",
            version = "0.1",
            metadata= [ {"title": "LSCE" , "href": "http://www.lsce.ipsl.fr/"} ],
            abstract="Calculates whether the magnitude of the ensemble mean is larger than the ensemble standard deviation.",
            )
        # input arguments    
        self.resource = self.addComplexInput(
            identifier="resource",
            title="NetCDF Files",
            abstract="NetCDF Files",
            minOccurs=1,
            maxOccurs=100,
            maxmegabites=5000,
            formats=[{"mimeType":"application/x-netcdf"}],
            )

        # output 
        
        self.delta = self.addComplexOutput(
            identifier="abs delta",
            title="magnitude of ensemble change",
            abstract="netCDF file containing abs delta",
            formats=[{"mimeType":"application/netcdf"}],
            asReference=True,
            )   

        self.ensstd = self.addComplexOutput(
            identifier="ensstd",
            title="std of ensemble mean across time",
            abstract="netCDF file containing std of mean across time",
            formats=[{"mimeType":"application/netcdf"}],
            asReference=True,
            ) 

        self.binmask = self.addComplexOutput(
            identifier="binmask",
            title="binmask",
            abstract="netCDF file where abs delta greater than ensstd",
            formats=[{"mimeType":"application/netcdf"}],
            asReference=True,
            )

    def execute(self):
        self.show_status('starting uncertainty process', 0)
    
        from flyingpigeon.modelUncertainty import modelUncertaintyWorker as muw
        
        ncfiles = self.getInputValues(identifier='resource')
        
        result, result2, result3  = muw(ncfiles)        
        
        self.delta.setValue( result ) #magnitude of model change

        self.ensstd.setValue( result2 ) #ensemble std

        self.binmask.setValue( result3 ) #delta > std
            
        self.show_status('uncertainty process done', 99)