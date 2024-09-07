#!/bin/bash
git reset --hard HEAD && \
  git reset --hard origin/main && \
  git fetch origin && \
  git reset --hard origin/main && \
  git pull origin main
