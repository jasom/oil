self: super: rec {
  python38 = super.python38.override {
    # Careful, we're using a different self and super here!
    packageOverrides = python-self: python-super: {
      typing-extensions = python-self.buildPythonPackage rec {
        pname = "typing_extensions";
        version = "3.7.4.2";

        src = python-super.fetchPypi {
          inherit pname version;
          sha256 = "79ee589a3caca649a9bfd2a8de4709837400dfa00b6cc81962a1e6a1815969ae";
        };

        checkInputs = super.lib.optional (python-self.pythonOlder "3.5") python-self.typing;

        # Error for Python3.6: ImportError: cannot import name 'ann_module'
        # See https://github.com/python/typing/pull/280
        doCheck = python-self.pythonOlder "3.6";

        checkPhase = ''
          cd src_py3
          ${python-self.python.interpreter} -m unittest discover
        '';

        meta = with super.lib; {
          description = "Backported and Experimental Type Hints for Python 3.5+";
          homepage = "https://github.com/python/typing";
          license = licenses.psfl;
          maintainers = with maintainers; [ pmiddend ];
        };
      };
      typing = python-self.buildPythonPackage rec {
        pname = "typing";
        version = "3.7.4.1";

        src = super.fetchPypi {
          inherit pname version;
          sha256 = "91dfe6f3f706ee8cc32d38edbbf304e9b7583fb37108fef38229617f8b3eba23";
        };

      # Error for Python3.6: ImportError: cannot import name 'ann_module'
      # See https://github.com/python/typing/pull/280
      # Also, don't bother on PyPy: AssertionError: TypeError not raised
      doCheck = python-self.pythonOlder "3.6" && !python-self.isPyPy;

      checkPhase = ''
        cd src
        ${python-self.interpreter} -m unittest discover
      '';

      meta = with super.lib; {
        description = "Backport of typing module to Python versions older than 3.5";
        homepage = "https://docs.python.org/3/library/typing.html";
        license = licenses.psfl;
      };
    };
      typed-ast = python-self.buildPythonPackage rec {
        pname = "typed-ast";
        version = "1.4.0";
        src = super.fetchFromGitHub{
          owner = "python";
          repo = "typed_ast";
          rev = version;
          sha256 = "sha256-y7/v3GL4c+WszDlpmCRKq8XItdJuT1ynKSMelwD6EFA=";
        };
        # Only works with Python 3.3 and newer;
        disabled = python-self.pythonOlder "3.3";
        # No tests in archive
        doCheck = false;
        meta = {
          homepage = "https://pypi.python.org/pypi/typed-ast";
          description = "a fork of Python 2 and 3 ast modules with type comment support";
          license = super.lib.licenses.asl20;
        };
      };
      mypy-extensions = python-self.buildPythonPackage rec {
        pname = "mypy-extensions";
        version = "0.4.3";

        # Tests not included in pip package.
        doCheck = false;

        src = super.fetchFromGitHub {
          rev = version;
          owner = "python";
          repo = "mypy_extensions";
          sha256 = "sha256-JjhbxX5DBAbcs1o2fSWywz9tot792q491POXiId+NyI=";
        };

        propagatedBuildInputs = if python-self.pythonOlder "3.5" then [ python-self.typing ] else [ ];

        meta = with super.lib; {
          description = "Experimental type system extensions for programs checked with the mypy typechecker";
          homepage    = "http://www.mypy-lang.org";
          license     = licenses.mit;
          maintainers = with maintainers; [ martingms lnl7 ];
        };
      };
      mypy =  python-self.buildPythonPackage rec {
        pname = "mypy";
        version = "0.780";
        #disabled = python-super.isPy3k;

#        src = super.fetchPypi {
#          inherit pname version;
#          sha256 = "4ef13b619a289aa025f2273e05e755f8049bb4eaba6d703a425de38d495d178d";
#        };

        src = super.fetchFromGitHub {
          owner = "python";
          repo = "mypy";
          fetchSubmodules = true;
          rev="v${version}";
          sha256 = "sha256-czwCx6ZjCu3CrVmbI6NbstzWM0GvuPTWJiiUhXSznu4=";
        };

        propagatedBuildInputs = [ python-self.typed-ast python-super.psutil python-self.mypy-extensions python-self.typing-extensions ];

        # Tests not included in pip package.
        doCheck = false;

        pythonImportsCheck = [
          "mypy"
          "mypy.types"
          "mypy.api"
          "mypy.fastparse"
          "mypy.report"
          ];

          meta = with super.lib; {
            description = "Optional static typing for Python";
            homepage    = "http://www.mypy-lang.org";
            license     = licenses.mit;
            maintainers = with maintainers; [ martingms lnl7 ];
          };
        };
#      mypy = python-super.mypy.overridePythonAttrs (origattrs: rec {
#        version = "0.780";
#        patches = [ ];
#        src = super.fetchFromGitHub {
#          owner = "python";
#          repo = "mypy";
#          rev="release-${version}";
# 7        sha256 = "sha256-ocRZLQwM/kR4ijb1G5XyEt0meR2t9IP275uCRlTXloE=";
#        };
#      });
    };
  };
  # nix-shell -p pythonPackages.my_stuff
  python38Packages = python38.pkgs;
}
