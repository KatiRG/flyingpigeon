import urlparse
import os
import wget
from ocgis import RequestDataset  # does not support NETCDF4
from netCDF4 import Dataset, num2date
from netCDF4 import MFDataset  # does not support NETCDF4
from flyingpigeon import config

import logging
logger = logging.getLogger(__name__)

GROUPING = ["day", "mon", "sem", "yr", "ONDJFM", "AMJJAS", "DJF", "MAM", "JJA", "SON",
            "Jan", 'Feb', "Mar", "Apr", "May", "Jun", 'Jul', "Aug", 'Sep', 'Oct', 'Nov', 'Dec']


def make_dirs(directory):
    """
    creates a dictionary if not already existing

    :param direcory: directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def check_creationtime(path, url):
    """
    Compares the creation time of an archive file with the file creation time of the local disc space.

    :param path: Path to the local file
    :param url: URL to the archive file

    :returns boolean: True/False (True if archive file is newer)
    """

    try:
        import urllib2
        import os
        import datetime
        import time

        u = urllib2.urlopen(url)
        meta = u.info()
        logger.info("Last Modified: " + str(meta.getheaders("Last-Modified")[0]))

        # CONVERTING HEADER TIME TO UTC TIMESTAMP
        # ASSUMING 'Sun, 28 Jun 2015 06:30:17 GMT' FORMAT
        meta_modifiedtime = time.mktime(datetime.datetime.strptime(
                            meta.getheaders("Last-Modified")[0], "%a, %d %b %Y %X GMT").timetuple())

        # file = 'C:\Path\ToFile\somefile.xml'
        if os.path.getmtime(path) < meta_modifiedtime:
            logger.info("local file is older than archive file.")
            newer = True
        else:
            logger.info("local file is up-to-date. Nothing to fetch.")
            newer = False
    except:
        msg = 'failed to check arichve and cache creation time assuming newer = False'
        logger.exception(msg)
        newer = False
    return newer


def download(url, cache=False):
    """
    Downloads URL using the Python wget module to the current directory.
    :param cache: if True then files will be downloaded to a cache directory.
    """
    try:
        if cache:
            parsed_url = urlparse.urlparse(url)
            filename = os.path.join(config.cache_path(), parsed_url.netloc, parsed_url.path.strip('/'))
            if os.path.exists(filename):
                logger.info('file already in cache: %s', os.path.basename(filename))
                if check_creationtime(filename, url):
                    logger.info('file in cache older than archive file, downloading: %s ', os.path.basename(filename))
                    os.remove(filename)
                    filename = wget.download(url, out=filename, bar=None)
            else:
                if not os.path.exists(os.path.dirname(filename)):
                    os.makedirs(os.path.dirname(filename))
                logger.info('downloading: %s', url)
                filename = wget.download(url, out=filename, bar=None)
                # make softlink to current dir
                # os.symlink(filename, os.path.basename(filename))
# filename = os.path.basename(filename)
        else:
            filename = wget.download(url, bar=None)
    except:
        logger.exception('failed to download data')
    return filename


def archive(resources, format='tar', dir_output='.', mode='w'):
    """
    compresses a list of files into an archive

    :param resources: list of files to be stored in archive
    :param format: archive format. Options: tar (default), zip
    :param dir_output: path to output folder (default current directory)
    :param mode: for format='tar':
                  'w' or 'w:'  open for writing without compression
                  'w:gz'       open for writing with gzip compression
                  'w:bz2'      open for writing with bzip2 compression
                  'w|'         open an uncompressed stream for writing
                  'w|gz'       open a gzip compressed stream for writing
                  'w|bz2'      open a bzip2 compressed stream for writing

                  for foramt='zip':
                  read "r", write "w" or append "a"

    :return str: archive path/filname.ext
    """
    from tempfile import mkstemp
    from os.path import basename

    logger.info('compressing files to archive')
    try:
        if isinstance(resources, str):
            resources = list([resources])

        resources_filter = [x for x in resources if x is not None]
        resources = resources_filter
    except Exception as e:
        msg = 'failed to prepare file list: %s' % e
        logger.debug(msg)

    if format == 'tar':
        import tarfile
        try:
            o1, archive = mkstemp(dir=dir_output, suffix='.tar')
            tar = tarfile.open(archive, mode)

            for f in resources:
                try:
                    tar.add(f, arcname=basename(f))
                except Exception as e:
                    msg = 'archiving failed for %s: %s' % (f, e)
                    logger.debug(msg)
                    raise(msg)
            tar.close()
        except Exception as e:
            msg = 'failed to compress into archive %s', e
            logger.exception(msg)
            raise(msg)
    elif format == 'zip':
        import zipfile

        logger.info('creating zip archive')
        try:
            o1, archive = mkstemp(dir=dir_output, suffix='.zip')
            zf = zipfile.ZipFile(archive, mode=mode)
            for f in resources:
                zf.write(f, basename(f))
            zf.close()
        except Exception as e:
            msg = 'failed to create zip archive: %s' % msg
            logger.debug(msg)
            raise
            # logger.info(print_info('zipfile_write.zip'))
    else:
        logger.error('no common archive format like: zip / tar')
    return archive


def archiveextract(resource, path='.'):
    """
    extracts archives (tar/zip)

    :param resource: list/str of archive files (if netCDF files are in list,
                     they are passed and returnd as well in the return)
    :param path: define a directory to store the results (default='.')

    :return list: [list of extracted files]
    """
    from tarfile import open
    import zipfile
    from os.path import basename, join

    try:
        if type(resource) is str:
            resource = [resource]
        files = []

        for archive in resource:
            try:
                if basename(archive).split('.')[1] == 'nc':
                    files.append(join(path, archive))
                elif basename(archive).split('.')[1] == 'tar':
                    tar = open(archive, mode='r')
                    tar.extractall()
                    files.extend([join(path, nc) for nc in tar.getnames()])
                    tar.close()
                elif basename(archive).split('.')[1] == 'zip':
                    zf = zipfile.open(archive, mode='r')
                    zf.extractall()
                    files.extend([join(path, nc) for nc in zf.filelist])
                    zf.close()
                else:
                    logger.debug('file extention unknown')
            except Exception as e:
                logger.debug('failed to extract sub archive: %s' % e)
    except Excepion as e:
        logger.debug('failed to extract archive resource: %s' % e)
    return files


def local_path(url):
    from urllib2 import urlparse
    url_parts = urlparse.urlparse(url)
    return url_parts.path


def calc_grouping(grouping):
    """
    translate time grouping abbreviation (e.g 'JJA') into the appropriate ocgis calc_grouping syntax

    :param grouping: time group abbreviation allowed values: "yr", "mon", "sem",
                     "ONDJFM", "AMJJAS", "DJF", "MAM", "JJA", "SON"

    :returns list: calc_grouping conformant to ocgis syntax
    """
    calc_grouping = ['year']  # default year
    if grouping == 'yr':
        calc_grouping = ['year']
    elif grouping == 'sem':
        calc_grouping = [[12, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11], 'unique']
    elif grouping == 'ONDJFM':
        calc_grouping = [[10, 11, 12, 1, 2, 3], 'unique']
    elif grouping == 'AMJJAS':
        calc_grouping = [[4, 5, 6, 7, 8, 9], 'unique']
    elif grouping == 'DJF':
        calc_grouping = [[12, 1, 2], 'unique']
    elif grouping == 'MAM':
        calc_grouping = [[3, 4, 5], 'unique']
    elif grouping == 'JJA':
        calc_grouping = [[6, 7, 8], 'unique']
    elif grouping == 'SON':
        calc_grouping = [[9, 10, 11], 'unique']
    elif grouping == 'day':
        calc_grouping = ['year', 'month', 'day']
    elif grouping == 'mon':
        calc_grouping = ['year', 'month']
    elif grouping == 'Jan':
        calc_grouping = [[1], 'unique']
    elif grouping == 'Feb':
        calc_grouping = [[2], 'unique']
    elif grouping == 'Mar':
        calc_grouping = [[3], 'unique']
    elif grouping == 'Apr':
        calc_grouping = [[4], 'unique']
    elif grouping == 'May':
        calc_grouping = [[5], 'unique']
    elif grouping == 'Jun':
        calc_grouping = [[6], 'unique']
    elif grouping == 'Jul':
        calc_grouping = [[7], 'unique']
    elif grouping == 'Aug':
        calc_grouping = [[8], 'unique']
    elif grouping == 'Sep':
        calc_grouping = [[9], 'unique']
    elif grouping == 'Oct':
        calc_grouping = [[10], 'unique']
    elif grouping == 'Nov':
        calc_grouping = [[11], 'unique']
    elif grouping == 'Dec':
        calc_grouping = [[12], 'unique']
    elif grouping in ['year', 'month']:
        calc_grouping = [grouping]
    else:
        msg = 'Unknown calculation grouping: %s' % grouping
        logger.debug(msg)
        raise Exception(msg)
    return calc_grouping


def drs_filename(resource, skip_timestamp=False, skip_format=False,
                 variable=None, rename_file=False, add_file_path=False):
    """
    generates filename according to the data reference syntax (DRS)
    based on the metadata in the resource.

    http://cmip-pcmdi.llnl.gov/cmip5/docs/cmip5_data_reference_syntax.pdf
    https://pypi.python.org/pypi/drslib

    :param add_file_path: if add_file_path=True, path to file will be added (default=False)
    :param resource: netcdf file
    :param skip_timestamp: if True then from/to timestamp != added to the filename
                           (default: False)
    :param variable: appropriate variable for filename, if not set (default), variable will
                      be determined. For files with more than one data variable,
                      the variable parameter has to be defined (default: )
                      example: variable='tas'
    :param rename_file: rename the file. (default: False)

    :returns str: DRS filename
    """
    from os import path, rename

    try:
        ds = Dataset(resource)
        if variable is None:
            variable = get_variable(resource)
        # CORDEX example: EUR-11_ICHEC-EC-EARTH_historical_r3i1p1_DMI-HIRHAM5_v1_day
        cordex_pattern = "{variable}_{domain}_{driving_model}_{experiment}_{ensemble}_{model}_{version}_{frequency}"
        # CMIP5 example: tas_MPI-ESM-LR_historical_r1i1p1
        cmip5_pattern = "{variable}_{model}_{experiment}_{ensemble}"
        filename = resource
        if ds.project_id == 'CORDEX' or ds.project_id == 'EOBS':
            filename = cordex_pattern.format(
                variable=variable,
                domain=ds.CORDEX_domain,
                driving_model=ds.driving_model_id,
                experiment=ds.experiment_id,
                ensemble=ds.driving_model_ensemble_member,
                model=ds.model_id,
                version=ds.rcm_version_id,
                frequency=ds.frequency)
        elif ds.project_id == 'CMIP5':
            # TODO: attributes missing in netcdf file for name generation?
            filename = cmip5_pattern.format(
                variable=variable,
                model=ds.model_id,
                experiment=ds.experiment,
                ensemble=ds.parent_experiment_rip
                )
        else:
            raise Exception('unknown project %s' % ds.project_id)
        ds.close()
    except:
        logger.exception('Could not read metadata %s', resource)
    try:
        # add from/to timestamp if not skipped
        if skip_timestamp is False:
            logger.debug("add timestamp")
            from_timestamp, to_timestamp = get_timerange(resource)
            logger.debug("from_timestamp %s", from_timestamp)
            filename = "%s_%s-%s" % (filename, int(from_timestamp), int(to_timestamp))

        # add format extension
        if skip_format is False:
            filename = filename + '.nc'

        pf = path.dirname(resource)
        # add file path
        if add_file_path is True:
            filename = path.join(pf, filename)

        # rename the file
        if rename_file is True:
            if path.exists(path.join(resource)):
                rename(resource, path.join(pf, filename))
    except:
        logger.exception('Could not generate DRS filename for %s', resource)

    return filename


def get_variable(resource):
    """
    detects processable variable name in netCDF file

    :param resource: NetCDF file(s)

    :returns str: variable name
    """
    rds = RequestDataset(resource)
    return rds.variable


def get_coordinates(resource):
    """
    reads out the values of latitude and longitude in a netCDF file

    :param resource: netCDF resource file

    :returns list, list: latitudes , longitudes
    """
    lats = None
    lons = None
    try:
        ds = Dataset(resource)
        if 'lat' in ds.variables.keys():
            lats = ds.variables['lat']
            lons = ds.variables['lon']
        elif 'rlat' in ds.variables.keys():
            ds.close()
            unrotate_pole(resource, write_to_file=True)
            ds = Dataset(resource)
            lats = ds.variables['lat']
            lons = ds.variables['lon']
        else:
            msg = 'could not find coordinates: %s ' % resource
            logger.debug(msg)
            raise Exception(msg)
        ds.close()
    except Exception as e:
        msg = 'failed to extract coordinates: %s ' % e
        logger.debug(msg)
        raise Exception(msg)
    return lats, lons


def get_domain(resource):
    """
    returns the domain of a netCDF file

    :param resource: netCDF file (metadata quality checked!)

    :return str: domain
    """
    try:
        ds = Dataset(resource)
        if 'CMIP' in ds.project_id or 'EUCLEIA' in ds.project_id:
            domain = None
            logger.debug('resource belongs to a global experiment project')
        elif 'CORDEX' in ds.project_id:
            domain = ds.CORDEX_domain
            logger.info('resource belongs to CORDEX')
        else:
            logger.debug('No known project_id found in meta data')
        ds.close()
    except Exception as e:
        logger.debug('Could not specify domain for %s: %s' % (resource, e))
    return domain


def get_frequency(resource):
    """
    returns the frequency as set in the metadata (see also metadata.get_frequency)

    :param resource: NetCDF file

    :return str: frequency
    """
    ds = Dataset(resource)

    try:
        frequency = ds.frequency
        logger.info('frequency written in the meta data:  %s', frequency)
    except Exception as e:
        msg = "Could not specify frequency for %s" % (resource)
        logger.exception(msg)
        raise Exception(msg)
    else:
        ds.close()
    return frequency


def get_values(resource, variable=None):
    """
    returns the values for a list of files of files belonging to one dataset

    :param resource: list of files
    :param variable: variable to be picked from the files (if not set, variable will be detected)

    :returs numpy.array: values
    """
    from numpy import squeeze
    if variable is None:
        variable = get_variable(resource)

    if type(resource) is str:
        ds = Dataset(resource)
    elif len(resource) == 1:
        ds = Dataset(resource)
    else:
        ds = MFDataset(resource)
    vals = squeeze(ds.variables[variable][:])
    return vals


def get_timerange(resource):
    """
    returns from/to timestamp of given netcdf file(s).

    :param resource: list of path(s) to netCDF file(s)

    :returns netcdf.datetime.datetime: start, end

    """
    start = end = None

    if type(resource) != list:
        resource = [resource]
    logger.debug('length of recources: %s files' % len(resource))

    try:
        if len(resource) > 1:
            ds = MFDataset(resource)
            time = ds.variables['time']
            print('MFDataset loaded for %s of files in resource:' % len(resource))
        else:
            ds = Dataset(resource[0])
            time = ds.variables['time']
            print('Dataset loaded for %s file in resource:' % len(resource))

        if (hasattr(time, 'units') and hasattr(time, 'calendar')) is True:
            s = num2date(time[0], time.units, time.calendar)
            e = num2date(time[-1], time.units, time.calendar)
        elif hasattr(time, 'units'):
            s = num2date(time[0], time.units)
            e = num2date(time[-1], time.units)
        else:
            s = num2date(time[0])
            e = num2date(time[-1])

        # TODO: include frequency
        start = '%s%s%s' % (s.year, str(s.month).zfill(2), str(s.day).zfill(2))
        end = '%s%s%s' % (e.year,  str(e.month).zfill(2), str(e.day).zfill(2))
        ds.close()
    except Exception as e:
        msg = 'failed to get time range: %s ' % e
        logger.exception(msg)
        ds.close()
        raise Exception(msg)
    return start, end

# def get_timestamps(resource):
#     """
#     !OBSOLETE!
#     replaced by get_timerange
#     """
#     try:
#         start = get_time(resource)[0]
#         end = get_time(resource)[-1]

#         from_timestamp = '%s%s%s'  % (start.year, str(start.month).zfill(2) ,str(start.day).zfill(2))
#         to_timestamp = '%s%s%s'  %   (end.year,  str(end.month).zfill(2) ,str(end.day).zfill(2))
#     except Exception as e:
#       msg = 'failed to get_timestamps'
#       logger.exception(msg)
#       raise Exception(msg)

#     return (from_timestamp, to_timestamp)


def get_time(resource, format=None):
    """
    returns all timestamps of given netcdf file as datetime list.

    :param resource: NetCDF file(s)
    :param format: if a format is provided (e.g format='%Y%d%m'), values will be converted to string
    :return : list of timesteps
    """
    if type(resource) != list:
        resource = [resource]

    try:
        if len(resource) > 1:
            ds = MFDataset(resource)
            time = ds.variables['time']
        else:
            ds = Dataset(resource[0])
        time = ds.variables['time']
    except:
        msg = 'failed to get time'
        logger.exception(msg)
        raise Exception(msg)

    try:
        if (hasattr(time, 'units') and hasattr(time, 'calendar')) is True:
            timestamps = num2date(time[:], time.units, time.calendar)
        elif hasattr(time, 'units'):
            timestamps = num2date(time[:], time.units)
        else:
            timestamps = num2date(time[:])
        ds.close()
        try:
            if format is not None:
                timestamps = [t.strftime(format=format) for t in timestamps]
        except:
            msg = 'failed to convert times to string'
            print msg
            logger.debug(msg)
    except:
        msg = 'failed to convert time'
        logger.exception(msg)
        raise Exception(msg)
    return timestamps


def aggregations(resource):
    """
    aggregates netcdf files by experiment. Aggregation examples:

    CORDEX: EUR-11_ICHEC-EC-EARTH_historical_r3i1p1_DMI-HIRHAM5_v1_day
    CMIP5:
    We collect for each experiment all files on the time axis:
    200101-200512, 200601-201012, ...

    Time axis is sorted by time.

    :param resource: list of netcdf files

    :return: dictionary with key=experiment
    """

    aggregations = {}
    for nc in resource:
        key = drs_filename(nc, skip_timestamp=True, skip_format=True)

        # collect files of each aggregation (time axis)
        if aggregations.has_key(key):
            aggregations[key]['files'].append(nc)
        else:
            aggregations[key] = dict(files=[nc])

    # collect aggregation metadata
    for key in aggregations.keys():
        # sort files by time
        aggregations[key]['files'] = sort_by_time(aggregations[key]['files'])
        # start timestamp of first file
        start, _ = get_timerange(aggregations[key]['files'][0])
        # end timestamp of last file
        _, end = get_timerange(aggregations[key]['files'][-1])
        aggregations[key]['from_timestamp'] = start
        aggregations[key]['to_timestamp'] = end
        aggregations[key]['start_year'] = int(start[0:4])
        aggregations[key]['end_year'] = int(end[0:4])
        aggregations[key]['variable'] = get_variable(aggregations[key]['files'][0])
        aggregations[key]['filename'] = "%s_%s-%s.nc" % (key, start, end)
    return aggregations


def rename_variable(resource, oldname=None, newname='newname'):
    """
    Change the variable name of a netCDF variable

    :param resource: path to netCDF input file
    :param oldname: variable name to be changed
    :param newname: variable name to be given

    :retunrs str: path to resource
    """
    try:
        if oldname is None:
            oldname = get_variable(resource)
        if oldname != newname:
            from netCDF4 import Dataset
            ds = Dataset(resource, mode='a')
            ds.renameVariable(oldname, newname)
            ds.close()
            logger.info('varname %s in netCDF renamed to %s' % (oldname, newname))
    except Exception as e:
        msg = 'failed to rename variable in target files %s ' % e
        logger.debug(msg)
        raise Exception(msg)


def sort_by_time(resource):
    from ocgis.util.helpers import get_sorted_uris_by_time_dimension

    if type(resource) == list and len(resource) > 1:
        sorted_list = get_sorted_uris_by_time_dimension(resource)
    elif type(resource) == str:
        sorted_list = [resource]
    else:
        sorted_list = resource
    return sorted_list


def sort_by_filename(resource, historical_concatination=False):
    """
    Sort a list of files with CORDEX-conformant file names.

    :param resource: netCDF file
    :param historical_concatination: if True (default=False), appropriate historial
                                    runs will be sorted to the rcp datasets
    :return  dictionary: {'drs_filename': [list of netCDF files]}
    """
    from os import path
    if type(resource) == str:
        resource = [resource]

    ndic = {}
    tmp_dic = {}

    try:
        if len(resource) > 1:
            logger.debug('sort_by_filename module start sorting %s files' % len(resource))
            # logger.debug('resource is list with %s files' % len(resource))
            try:  # if len(resource) > 1:
                # collect the different experiment names
                for nc in resource:
                    logger.info('file: %s' % nc)
                    p, f = path.split(path.abspath(nc))
                    n = f.split('_')
                    bn = '_'.join(n[0:-1])  # skipping the date information in the filename
                    ndic[bn] = []  # dictionary containing all datasets names
                logger.info('found %s datasets', len(ndic.keys()))
            except Exception as e:
                logger.exception('failed to find names of datasets! %s ' % e)
            logger.info('check for historical/RCP datasets')
            try:
                if historical_concatination is True:
                    # select only necessary names
                    if any("_rcp" in s for s in ndic.keys()):
                        for key in ndic.keys():
                            if 'historical' in key:
                                ndic.pop(key)
                        logger.info('historical data set names removed from dictionary')
                    else:
                        logger.info('no RCP dataset names found in dictionary')
            except Exception as e:
                logger.exception('failed to pop historical data set names! %s ' % e)
            logger.info('start sorting the files')
            try:
                for key in ndic:
                    try:
                        if historical_concatination is False:
                            for n in resource:
                                if '%s_' % key in n:
                                    ndic[key].append(path.join(p, n))

                        elif historical_concatination is True:
                            key_hist = key.replace('rcp26', 'historical').\
                                        replace('rcp45', 'historical').replace('rcp65', 'historical').\
                                        replace('rcp85', 'historical')
                            for n in resource:
                                if '%s_' % key in n or '%s_' % key_hist in n:
                                    ndic[key].append(path.join(p, n))
                        else:
                            logger.error('append file paths to dictionary for key %s failed' % key)
                        ndic[key].sort()
                    except:
                        logger.exception('failed for %s ' % key)
            except:
                logger.exception('failed to populate the dictionary with appropriate files')
            for key in ndic.keys():
                try:
                    ndic[key].sort()
                    start, end = get_timerange(ndic[key])
                    newkey = key+'_'+start+'-'+end
                    tmp_dic[newkey] = ndic[key]
                except:
                    msg = 'failed to sort the list of resources and add dates to keyname: %s' % key
                    logger.exception(msg)
                    raise Exception(msg)
        elif len(resource) == 1:
            p, f = path.split(path.abspath(resource[0]))
            tmp_dic[f.replace('.nc', '')] = path.abspath(resource[0])
            logger.debug('only one file! Nothing to sort, resource is passed into dictionary')
        else:
            logger.debug('sort_by_filename module failed: resource is not 1 or >1')
        logger.info('sort_by_filename module done: %s datasets found' % len(ndic))
    except:
        msg = 'failed to sort files by filename'
        logger.exception(msg)
        raise Exception(msg)
    return tmp_dic


def has_variable(resource, variable):
    success = False
    try:
        rd = RequestDataset(uri=resource)
        success = rd.variable == variable
    except:
        logger.exception('has_variable failed.')
        raise
    return success


def searchfile(pattern, base_dir):
    """
    searches recursive for files with an given pattern,

    :param pattern: file name pattern including wildcards (e.g. tas_*_day_*.nc)
    :param base_dir: base direcory of the direcory tree

    return:  list of fitting files
    """

    from os import path, walk
    import fnmatch

    nc_list = []
    for root, dir, files in walk(base_dir):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                nc_list.extend([path.join(root, name)])

    return nc_list

# def get_dimension_map(resource):
#   OBSOLETE
#   """ returns the dimension map for a file, required for ocgis processing.
#   file must have a DRS-conformant filename (see: utils.drs_filename())
#
#   :param resource: str input file path
#   """
#   from os.path import basename
#   file_name = basename(resource)
#
#   dim_map1 = {'X': {'variable': 'lon', 'dimension': 'x', 'pos': 2},
#               'Y': {'variable': 'lat', 'dimension': 'y', 'pos': 1},
#               'T': {'variable': 'time', 'dimension': 'time', 'pos': 0}}
#
#   dim_map2 = {'X': {'variable': 'lon', 'dimension': 'x', 'pos': 2},
#               'Y': {'variable': 'lat', 'dimension': 'y', 'pos': 1},
#               'T': {'variable': 'time', 'dimension': 'time', 'pos': 0, 'bounds': 'time_bnds'}}
#
#   dim_map3 = {'X': {'variable': 'rlon', 'dimension': 'x', 'pos': 2},
#               'Y': {'variable': 'rlat', 'dimension': 'y', 'pos': 1},
#               'T': {'variable': 'time', 'dimension': 'time', 'pos': 0 }}
#
#   dim_map4 = {'X': {'variable': 'x', 'dimension': 'x', 'pos': 2},
#               'Y': {'variable': 'y', 'dimension': 'y', 'pos': 1},
#               'T': {'variable': 'time', 'dimension': 'time', 'pos': 0 }}
#
#
#   dim_map5  = {'X': {'variable': 'Actual_longitude', 'dimension': 'x', 'pos': 2},
#                  'Y': {'variable': ' Actual_latitude', 'dimension': 'y', 'pos': 1},
#                  'T': {'variable': 'time', 'dimension': 'time', 'pos': 0 }}
#
#
#   if 'CM5A-MR_WRF331F' in file_name:
#     dimension_map = dim_map1
#   elif 'CNRM-CM5_CNRM-ALADIN53' in file_name:
#     dimension_map = dim_map1
#   elif 'MPI-ESM-LR_REMO019' in file_name:
#     dimension_map = dim_map1
#   elif 'CLMcom-CCLM4-8-17' in file_name:
#     dimension_map = dim_map1
#   elif '_EOBS_observation_' in file_name:
#     dimension_map = dim_map5

#   #elif 'KNMI-RACMO22E' in file_name:
#     #dimension_map = dim_map1
#   else:
#     dimension_map = None
#   return dimension_map

def unrotate_pole(resource, write_to_file=True):
    """
    Calculates the unrotatated coordinates for a rotated pole grid

    :param resource: netCDF file

    :return list: lats, lons
    """
    from numpy import reshape, repeat
    from iris.analysis import cartography as ct
    ds = Dataset(resource, mode='a')

    if 'lat' in ds.variables.keys():
        logger.info('coordinates already unrotated')
        lats = ds.variables['lat'][:]
        lons = ds.variables['lon'][:]

    else:
        try:
            if 'rotated_latitude_longitude' in ds.variables:
                rp = ds.variables['rotated_latitude_longitude']
            elif 'rotated_pole' in ds.variables:
                rp = ds.variables['rotated_pole']
            else:
                logger.debug('rotated pole variable not found')
            pole_lat = rp.grid_north_pole_latitude
            pole_lon = rp.grid_north_pole_longitude
        except Exception as e:
            logger.debug('failed to find rotated_pole coordinates: %s' % e)
        try:
            if 'rlat' in ds.variables:
                rlats = ds.variables['rlat']
                rlons = ds.variables['rlon']

            if 'x' in ds.variables:
                rlats = ds.variables['y']
                rlons = ds.variables['x']
        except Exception as e:
            logger.debug('failed to read in rotated coordiates %s' % e)

        try:
            rlons_i = reshape(rlons, (1, len(rlons)))
            rlats_i = reshape(rlats, (len(rlats), 1))
            grid_rlats = repeat(rlats_i, (len(rlons)), axis=1)
            grid_rlons = repeat(rlons_i, (len(rlats)), axis=0)
        except Exception as e:
            logger.debug('failed to repeat coordinates %s' % e)

        lons, lats = ct.unrotate_pole(grid_rlons, grid_rlats, pole_lon, pole_lat)

    if write_to_file is True:
        lat = ds.createVariable('lat', 'f8', ('rlat', 'rlon'))
        lon = ds.createVariable('lon', 'f8', ('rlat', 'rlon'))

        lon.standard_name = "longitude"
        lon.long_name = "longitude coordinate"
        lon.units = 'degrees_east'
        lat.standard_name = "latitude"
        lat.long_name = "latitude coordinate"
        lat.units = 'degrees_north'

        lat[:] = lats
        lon[:] = lons
    ds.close()

    return lats, lons


class FreeMemory(object):
    """
    Non-cross platform way to get free memory on Linux. Note that this code
    uses the key word as, which is conditionally Python 2.5 compatible!
    If for some reason you still have Python 2.5 on your system, add in the head
    of your code, before all imports:
    from __future__ import with_statement
    """

    def __init__(self, unit='kB'):
        with open('/proc/meminfo', 'r') as mem:
            lines = mem.readlines()
        self._tot = int(lines[0].split()[1])
        self._free = int(lines[1].split()[1])
        self._buff = int(lines[2].split()[1])
        self._cached = int(lines[3].split()[1])
        self._shared = int(lines[20].split()[1])
        self._swapt = int(lines[14].split()[1])
        self._swapf = int(lines[15].split()[1])
        self._swapu = self._swapt - self._swapf
        self.unit = unit
        self._convert = self._faktor()

    def _faktor(self):
        """determine the conversion factor"""
        if self.unit == 'kB':
            return 1
        if self.unit == 'k':
            return 1024.0
        if self.unit == 'MB':
            return 1/1024.0
        if self.unit == 'GB':
            return 1/1024.0/1024.0
        if self.unit == '%':
            return 1.0/self._tot
        else:
            raise Exception("Unit not understood")

    @property
    def total(self):
        return self._convert * self._tot

    @property
    def used(self):
        return self._convert * (self._tot - self._free)

    @property
    def used_real(self):
        """memory used which != cache or buffers"""
        return self._convert * (self._tot - self._free - self._buff - self._cached)

    @property
    def shared(self):
        return self._convert * (self._tot - self._free)

    @property
    def buffers(self):
        return self._convert * (self._buff)

    @property
    def cached(self):
        return self._convert * self._cached

    @property
    def user_free(self):
        """This is the free memory available for the user"""
        return self._convert * (self._free + self._buff + self._cached)

    @property
    def swap(self):
        return self._convert * self._swapt

    @property
    def swap_free(self):
        return self._convert * self._swapf

    @property
    def swap_used(self):
        return self._convert * self._swapu
