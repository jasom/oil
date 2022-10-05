{
  description = "Python 3.9 development environment";
  inputs.mach-nix.url = "github:DavHau/mach-nix";
  outputs = { self, nixpkgs, mach-nix }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs {
      inherit system;
      overlays = [
        (import ./nix-deps/test-shells.nix)
        (import ./nix-deps/mypy-env.nix)
    ];
    };
    pythonEnv = (pkgs.python38.buildEnv.override {
          extraLibs = [ pkgs.python38Packages.mypy ];
        });
    oil-mypy = pkgs.callPackage nix-deps/mypy.nix {};
    oil-deps = pkgs.stdenv.mkDerivation {
      name    = "oil-DEPS";

      phases = [ "installPhase" ];
      installPhase = ''
        mkdir -p $out/
        ln -s ${pkgs.cmark}/lib/libcmark.so "$out/"
        mkdir -p $out/mycpp-venv/bin/
        ln -s ${pythonEnv} $out/mycpp-venv/env
        echo ":" > $out/mycpp-venv/bin/activate
        cat <<EOF > $out/python3
        #!/bin/sh
        $out/mycpp-venv/env/bin/python3 "\$@"
        EOF
        chmod +x $out/python3
      '';
    };
  in {
    devShells.${system}.default = pkgs.mkShell {
      buildInputs = with pkgs; [
        gawk readline ninja cmake openssl libffi zlib
        python27Full
        busybox
        re2c
        git
        pythonEnv 
        #python27Packages.virtualenv
        oiltest_bash
        oiltest_dash
        oiltest_mksh
        oiltest_yash
        oiltest_zsh
      ];

      shellHook = ''
          rm -f ../oil_DEPS # No -r so it fails if it's a directory
          ln -s ${oil-deps} ../oil_DEPS
          build/py.sh all
          test/spec.sh smoke
          #set -x
          #bin/osh -c 'echo hi'
          #set +x
      '';          
    };
  };
}
