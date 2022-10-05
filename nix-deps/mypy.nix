{ stdenv, fetchFromGitHub, ... }:
stdenv.mkDerivation rec {
  pname = "oil-mypy";
  version = "0.780";
  src = fetchFromGitHub {
    owner = "python";
    repo = "mypy";
    rev="release-${version}";
    sha256 = "sha256-ocRZLQwM/kR4ijb1G5XyEt0meR2t9IP275uCRlTXloE=";
  };
  installPhase = ''
    mkdir -p $out
    cp -a $src/* $src/.[!.]* $out/
  '';
}
