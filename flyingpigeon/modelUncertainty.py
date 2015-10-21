from malleefowl import wpslogging as logging
logger = logging.getLogger(__name__)

def modelUncertaintyWorker(resource):
  """retuns the result
  
  :param resource: list of pathes to netCDF files
  """
  from cdo import Cdo
  cdo = Cdo()
  from flyingpigeon.utils import check_timestepps

  # check resource for consistency
  resource_qc =  check_timestepps(resource)  
  
  try: 
    # ensemble mean 
    nc_ensmean = cdo.ensmean(input = resource_qc, output = 'nc_ensmean.nc')    
    logger.info('ensmean calculations done')
  except Exception as e: 
    logger.error('ensmean calculations failed: %s ' % e )

  try:     
    #nc_delta = nc_ensmean(lastpt) - nc_ensmean(firstpt)    
    nc_laststep = cdo.seltimestep('-1', input = nc_ensmean, output = 'nc_laststep.nc')
    nc_firststep = cdo.seltimestep(1, input = nc_ensmean, output = 'nc_firststep.nc')
    nc_delta = cdo.sub(input = [nc_laststep, nc_firststep], output = 'nc_delta.nc')
    logger.info('delta calculation done')
  except Exception as e: 
    logger.error('delta calculation failed: %s ' % e )  

  try: 
    # ensemble std    
    nc_ensstd = cdo.ensstd(input = resource_qc, output = 'nc_ensstd.nc')
    logger.info('std calculation done')
  except Exception as e: 
    logger.error('std calculation failed: %s ' % e )

  try:
    # compute positive mask: if nc_delta > nc_enssstd
    nc_level = cdo.mulc(1, input = nc_ensstd, output = 'nc_level.nc')
    nc_binmask = cdo.gt(input = [nc_delta, nc_level], output = 'nc_binmask.nc')
    logger.info('calculated mask')
  except Exception as e: 
    logger.error('mask calculation failed: %s ' % e )

  
  #if > const
  #cdo.gtc('arg', input=infile, ontput=outfile)

  # mean + sigma as a mask 
  # sigma1 = cdo.fldstd(input = nc_ensmean, output = 'nc_sigma1.nc')
  # mask 
  
  # mean + 2* sigma as a mask
  
  # merge to on result netCDF
  # cdo.merge(input=[file1, file2], output='result.nc')

  result = nc_laststep  #nc_delta    #ensmean[lastpt] - ensmean[0] 
  result2 = nc_ensstd  #std of ensmean
  result3 = nc_binmask #delta > std
  
  return result, result2, result3