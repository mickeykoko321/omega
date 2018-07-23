Chain Module
============

This module has been created to be able to deal with Future's chains. As a future has different expiries and maturities
this was necessary.
The chain will hold information about the different maturities available with the expiry or last date (which can be
either FND or LTD).


A basic example to create a chain:

.. code-block:: Python

    # Import the chain module first
    import omega.core.chain as occ

    # Create a chain (in this example it will be a chain of spreads)
    fc = occ.FutureChain('FC', oci.FutureType.Spread)
    # Initialize the contracts (and the data)
    fc.initialize_contracts(occ.Status.Active, initialize_data=True)

There are various options in the chain initialization and in the contracts.