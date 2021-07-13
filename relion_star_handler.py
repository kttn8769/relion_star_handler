import os
import datetime

import numpy as np
import pandas as pd


class RelionMetaData:
    """RELION metadata handling class.

    Parameters
    ----------
    df_particles : pandas.DataFrame
        DataFrame containing particle data block contents.

    df_optics : pandas.DataFrame, optional
        DataFrame containing optics group data block contents. By default None

    starfile : string
        starfile name
    """
    def __init__(self, df_particles, df_optics=None, starfile=None):
        # data_ block in RELION 2.x/3.0, data_particles block in RELION 3.1
        self.df_particles = df_particles
        # data_optics block in RELION 3.1
        self.df_optics = df_optics
        self.starfile = starfile

    @classmethod
    def load(cls, starfile):
        """Load RELION metadata from a particle star file.

        Parameters
        ----------
        starfile : string
            star file

        Returns
        -------
        RelionMetaData
            RelionMetaData class instance.
        """

        with open(starfile, 'r') as f:
            # Check RELION version
            relion31 = None
            for line in f:
                words = line.strip().split()
                if len(words) == 0:
                    continue
                elif words[0] == 'data_optics':
                    relion31 = True
                    break
                elif words[0] == 'data_':
                    relion31 = False
                    break
                elif words[0][0] == '#':
                    # Comment line
                    continue
            assert relion31 is not None, f'The starfile {starfile} is invalid.'

        # Load starfile
        if relion31:
            df_particles, df_optics = cls._load_relion31(starfile)
        else:
            df_particles = cls._load_relion(starfile)
            df_optics = None
        return cls(df_particles, df_optics, starfile)

    @classmethod
    def _load_relion31(cls, starfile):
        """Load RELION 3.1 style starfile

        Parameters
        ----------
        starfile : string
            RELION 3.1 style star file

        Returns
        -------
        df_particles : pandas.DataFrame
            dataframe containing particle data block

        df_optics : pandas.DataFrame
            dataframe containing optics group data block.
        """

        with open(starfile, 'r') as f:
            headers_optics, data_optics = cls._read_block(f, 'data_optics')
            headers_particles, data_particles = cls._read_block(
                f, 'data_particles')
        df_optics = pd.DataFrame(data_optics, columns=headers_optics)
        df_particles = pd.DataFrame(data_particles, columns=headers_particles)
        return df_particles, df_optics

    @classmethod
    def _load_relion(cls, starfile):
        """Load RELION 2.x/3.0 style starfile

        Parameters
        ----------
        starfile : string
            RELION 2.x/3.0 style starfile

        Returns
        -------
        pandas.DataFrame
            dataframe containing data block
        """

        with open(starfile, 'r') as f:
            headers, data = cls._read_block(f, 'data_')
        df = pd.DataFrame(data, columns=headers)
        return df

    @classmethod
    def _read_block(cls, f, blockname):
        """Read data block from starfile

        Parameters
        ----------
        f : file-like object
            File-like object of starfile

        blockname : string
            Data block name to read.

        Returns
        -------
        headers : list of strings
            Metadata labels

        body : ndarray
            Metadatas
        """

        # Get to the block (data_, data_optics, data_particles, etc...)
        for line in f:
            if line.startswith(blockname):
                break
        # Get to header loop
        for line in f:
            if line.startswith('loop_'):
                break
        # Get list of column headers
        headers = []
        for line in f:
            if line.startswith('_'):
                headers.append(line.strip().split()[0])
            else:
                break
        # All subsequent lines until empty line is the data block body
        body = [line.strip().split()]
        for line in f:
            if line.strip() == '':
                break
            else:
                body.append(line.strip().split())
        body = np.array(body)

        assert len(headers) == body.shape[1]
        return headers, body

    def write(self, outdir, outfile_rootname):
        """Save metadata in file

        Parameters
        ----------
        outdir : string
            Output directory.

        outfile_rootname : string
            Output file rootname.
        """

        os.makedirs(outdir, exist_ok=True)
        outfile = os.path.join(outdir, outfile_rootname + '.star')
        with open(outfile, 'w') as f:
            f.write('# Created by cryoPICLS at {}\n'.format(
                datetime.datetime.now()))
            f.write('\n')
            if self.df_optics is not None:
                self._write_block(f, 'data_optics', self.df_optics)
                self._write_block(f, 'data_particles', self.df_particles)
            else:
                self._write_block(f, 'data_', self.df_particles)

    def _write_block(self, f, blockname, df):
        """Write data block as star format

        Parameters
        ----------
        f : File-like object
            Star file object
        blockname : string
            Data block name (e.g. data_optics)
        df : pandas.DataFrame
            DataFrame containing metadata labels and metadatas
        """

        f.write(blockname.strip())
        f.write('\n\n')
        f.write('loop_\n')
        f.write('\n'.join(df.columns))
        f.write('\n')
        for i in df.index:
            f.write(' '.join(df.loc[i]))
            f.write('\n')
        f.write('\n')

    def iloc(self, idxs):
        """Fancy indexing.

        Parameters
        ----------
        idxs : array-like
            Indices to select.

        Returns
        -------
        RelionMetaData
            New metadata object with the selected rows.
        """

        df_particles_new = self.df_particles.iloc[idxs]
        return self.__class__(df_particles=df_particles_new,
                              df_optics=self.df_optics)
