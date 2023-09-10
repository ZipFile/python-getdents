#!/bin/bash
# Based on https://github.com/pypa/python-manylinux-demo/blob/master/travis/build-wheels.sh
# Build steps:
# sudo rm -r getdents.egg-info build getdents/*.so
# docker run -it --rm -v `pwd`:/io -w /io -e PLAT=manylinux_2_28_x86_64 quay.io/pypa/manylinux_2_28_x86_64
# docker run -it --rm -v `pwd`:/io -w /io -e PLAT=musllinux_1_2_x86_64 quay.io/pypa/musllinux_1_2_x86_64
set -e -u -x
export WORKDIR=/io
export WHEELHOUSE="$WORKDIR/wheelhouse/"

function repair_wheel {
    wheel="$1"
    if ! auditwheel show "$wheel"; then
        echo "Skipping non-platform wheel $wheel"
    else
        auditwheel repair "$wheel" --plat "$PLAT" -w "$WHEELHOUSE"
    fi
}

if command -v yum &> /dev/null; then
    yum install -y git
fi

if command -v apk &> /dev/null; then
    # seems like musllinux image does not contain gcc
    apk add build-base git
fi

for PYBIN in /opt/python/*/bin; do
    if [[ $PYBIN =~ [cp]p3[67]\- ]]; then
      continue
    fi

    "${PYBIN}/pip" wheel "$WORKDIR" --no-deps -w "$WHEELHOUSE"
done

for whl in "$WHEELHOUSE"/*-linux_x86_64.whl; do
    repair_wheel "$whl"
    rm "$whl"
done

for PYBIN in /opt/python/*/bin; do
    if [[ $PYBIN =~ [cp]p3[67]\- ]]; then
      continue
    fi

    # https://github.com/pypa/pip/issues/11440
    "${PYBIN}/pip" install pytest pytest-cov
    "${PYBIN}/pip" install getdents --only-binary ":all:" --no-index -f "$WHEELHOUSE"
    (cd "$WORKDIR"; "${PYBIN}/py.test" -p no:cacheprovider)
done
