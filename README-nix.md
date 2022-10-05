Building with Nix:

1. This has only been tested with Nix 2.8.1
2. You will need to make sure that "../oil_DEPS" does not exist
3. To enter the Nix development environment run
   `nix --experimental-features 'nix-command flakes' develop`
   - Note: This will take a bit of time the first time you run it as all
     dependencies are built; future runs will be faster due to caching.
4. When it is done, the py version of osh should be built

At the shell you are now in, you should be able to:

- Run the spec tests (though not all currently pass)
- Build the cpp version of osh_eval
